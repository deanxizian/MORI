"""USB display heartbeat. No motor imports or actuator access in this module.

The worker owns all serial I/O; the 200 Hz controller only touches shared state.
A completed LCD frame must acknowledge the requested state. CAM expires active
red after 350 ms without reception; a frozen control loop stops host heartbeats.
This is an operator cue, not an emergency stop or proof of mechanical balance.
Completed red-on/off frames request one/two local CAM success tones. The worker
paces tones without blocking the control loop; no cloud or actuator access.
"""
import argparse
import json
from pathlib import Path
import re
import threading
import time

PORT='/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_90:70:69:FE:68:6C-if00'
IDENTITY=(0x303a,0x1001,'90:70:69:FE:68:6C')
ACK=re.compile(rb'MORI_MOTION_ACK (\d+) ([01])')
HEARTBEAT_S=.08
CONTROL_LIFETIME_S=.15
ACK_LIFETIME_S=.45
# The deployed success OGG is about 1.02 s; leave an audible gap between repeats.
SOUND_GAP_S=1.35


class IndicatorError(RuntimeError):
    pass


class CamConsole:
    """Bounded exclusive console I/O without toggling ESP reset modem lines."""
    def __init__(self,path,*,read_timeout=.01,write_timeout=.05):
        import fcntl
        import os
        import termios
        import tty
        self.fd=None
        self.read_timeout=read_timeout
        self.write_timeout=write_timeout
        fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            tty.setraw(fd)
            settings=termios.tcgetattr(fd)
            settings[2]&=~termios.HUPCL
            settings[4]=settings[5]=termios.B115200
            termios.tcsetattr(fd,termios.TCSANOW,settings)
            self.fd=fd
        except BaseException:
            os.close(fd)
            raise

    def reset_input_buffer(self):
        import termios
        termios.tcflush(self.fd,termios.TCIFLUSH)

    def read(self,n):
        import os
        import select
        ready,_,_=select.select([self.fd],[],[],self.read_timeout)
        if not ready:return b''
        try:data=os.read(self.fd,n)
        except BlockingIOError:return b''
        if not data:raise IndicatorError('cam_console_disconnected')
        return data

    def write(self,data):
        import os
        import select
        deadline=time.monotonic()+self.write_timeout
        sent=0
        while sent<len(data):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise IndicatorError('cam_console_write_timeout')
            _,ready,_=select.select([],[self.fd],[],remaining)
            if not ready:raise IndicatorError('cam_console_write_timeout')
            try:n=os.write(self.fd,data[sent:])
            except BlockingIOError:continue
            if n<=0:raise IndicatorError('cam_incomplete_write')
            sent+=n
        return sent

    def close(self):
        import os
        if self.fd is not None:
            os.close(self.fd)
            self.fd=None


class CamIndicator:
    def __init__(self,report,*,port=None,now=time.monotonic,active_red=True):
        if type(active_red) is not bool:
            raise ValueError('indicator_active_red_must_be_boolean')
        self.report=report
        self.active_red=active_red
        self.port=port
        self.now=now
        self.lock=threading.Lock()
        self.stop=threading.Event()
        self.wake=threading.Event()
        self.thread=None
        self.active_since=None
        self.tick_at=None
        self.change_at=0.
        self.ack_at=None
        self.ack_visible=False
        self.ack_token=None
        self.ready=False
        self.error=None
        self.first_ack=False
        self.sound_active=False
        self.sound_pending=[]
        self.report.update(protocol=1,port=PORT,cam_ttl_ms=350,control_ttl_ms=150,
                           cue_semantics=('balance_compensation_red' if active_red
                                          else 'operator_held_diagnostic_red_off'),
                           lcd_ack_timeout_ms=450,ack_count=0,events=[],
                           sound=dict(command='b',source='CAM_local_OGG_SUCCESS',
                                      start_tones=1 if active_red else 0,
                                      stop_tones=2 if active_red else 0,gap_s=SOUND_GAP_S,
                                      trigger='completed_LCD_frame_edge',sent=0))

    def _event(self,name,**details):
        self.report['events'].append(dict(event=name,t=self.now(),**details))

    def _write(self,data):
        if self.port.write(data)!=len(data):raise IndicatorError('cam_incomplete_write')

    def _line(self,line):
        if b'MORI_MOTION_READY v=1 ttl_ms=350' in line:self.ready=True
        match=ACK.search(line)
        if not match:return
        token=int(match[1]);visible=bool(int(match[2]));t=self.now()
        if token>0xffffffff:return
        with self.lock:
            # An expiry ACK reuses a token but changes visible. Duplicate
            # buffered lines cannot renew the freshness watchdog.
            if (token,visible)==(self.ack_token,self.ack_visible):return
            self.ack_at=t;self.ack_token=token;self.ack_visible=visible
            self.report['ack_count']+=1
            if not self.active_red:
                # A held speed diagnostic must never look like permission
                # to release the body. Retain the completed-frame watchdog,
                # but require red OFF and never queue balance start/stop tones.
                if visible:self.error='held_diagnostic_unexpected_red_frame'
                return
            if visible and self.active_since is not None and not self.first_ack:
                self.first_ack=True
                self._event('red_frame_ack',latency_ms=(t-self.active_since)*1000)
            # Initial off ACKs and repeated heartbeat tokens stay silent. Do
            # not announce a buffered on frame after stop or control expiry.
            if visible and not self.sound_active and self.active_since is not None and not self.error:
                self.sound_active=True
                self.sound_pending=[(t,'start',1,token)]
            elif not visible and self.sound_active:
                self.sound_active=False
                self.sound_pending=[(t,'stop',1,token),(t+SOUND_GAP_S,'stop',2,token)]

    def _sound_tick(self):
        with self.lock:
            if not self.sound_pending or self.sound_pending[0][0]>self.now():return
            _,edge,number,token=self.sound_pending.pop(0)
            if edge=='start' and (self.active_since is None or self.error):return
        # Existing firmware command queues the embedded tone on its audio
        # task. Never sleep here or perform this I/O from the 200 Hz controller.
        self._write(b'b')
        with self.lock:
            self.report['sound']['sent']+=1
            self._event('sound_command_sent',edge=edge,number=number,ack_token=token)

    def __enter__(self):
        if self.port is None:
            from serial.tools import list_ports
            matches=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==IDENTITY]
            if len(matches)!=1 or Path(PORT).resolve()!=Path(matches[0].device):
                raise IndicatorError('cam_identity_missing_or_ambiguous')
            self.port=CamConsole(PORT)
            self.report['transport']='exclusive_raw_tty_no_modem_line_changes'
        try:
            self.port.reset_input_buffer()
            self._write(b'C')
            deadline=self.now()+3.
            pending=b''
            while self.now()<deadline and not self.ready:
                pending+=self.port.read(1024)
                lines=pending.split(b'\n');pending=lines.pop()[-4096:]
                for line in lines:self._line(line)
            if not self.ready:raise IndicatorError('cam_indicator_firmware_not_ready')
            # Discard any earlier ACK: require an off frame for this connection.
            self.ack_at=None
            self.change_at=self.now()
            self._write(b'm')
            self.thread=threading.Thread(target=self._worker,name='cam-indicator',daemon=True)
            self.thread.start()
            deadline=self.now()+2.
            while self.now()<deadline:
                if self.error:raise IndicatorError(self.error)
                if self.ack_at is not None and self.ack_at>=self.change_at and not self.ack_visible:
                    self._event('ready_off_frame_ack')
                    return self
                time.sleep(.01)
            raise IndicatorError('cam_off_frame_not_acknowledged')
        except BaseException:
            self.close()
            raise

    def _worker(self):
        pending=b'';last_send=0.;last_state=None
        try:
            while not self.stop.is_set():
                t=self.now()
                with self.lock:
                    active=self.active_since is not None
                    if active and (self.tick_at is None or t-self.tick_at>CONTROL_LIFETIME_S):
                        self.error='control_heartbeat_expired'
                        active=False
                    if self.error:active=False
                if active!=last_state or t-last_send>=HEARTBEAT_S:
                    self._write(b'M' if active and self.active_red else b'm')
                    last_send=t;last_state=active
                pending+=self.port.read(1024)
                lines=pending.split(b'\n');pending=lines.pop()[-4096:]
                for line in lines:self._line(line)
                self._sound_tick()
                self.wake.wait(.005);self.wake.clear()
        except Exception as exc:
            with self.lock:self.error='cam_link_error: '+type(exc).__name__
        finally:
            try:self._write(b'm')
            except Exception:pass

    def check(self):
        with self.lock:
            if self.error:raise IndicatorError(self.error)
            t=self.now()
            grace=self.active_since if self.active_since is not None else self.change_at
            expected=self.active_since is not None and self.active_red
            fresh=(self.ack_at is not None and t-self.ack_at<=ACK_LIFETIME_S and
                   self.ack_visible==expected and self.ack_at>=grace)
            if not fresh and t-grace>ACK_LIFETIME_S:
                raise IndicatorError('cam_display_ack_stale_or_wrong_state')

    def tick(self):
        self.check()
        with self.lock:
            self.tick_at=self.now()
            if self.active_since is None:
                self.active_since=self.tick_at;self.change_at=self.tick_at
                self.first_ack=False
                self._event('compensation_active' if self.active_red else 'held_diagnostic_active')
        self.wake.set()

    def deactivate(self):
        with self.lock:
            if self.active_since is not None:
                self._event('compensation_stopped' if self.active_red else 'held_diagnostic_stopped')
            self.active_since=None;self.tick_at=None;self.change_at=self.now()
        self.wake.set()

    def close(self):
        if self.thread is not None:
            self.deactivate()
            deadline=self.now()+.6+SOUND_GAP_S
            while self.now()<deadline and self.thread.is_alive():
                with self.lock:
                    done=(self.ack_at is not None and self.ack_at>=self.change_at and
                          not self.ack_visible and not self.sound_pending)
                if done:break
                time.sleep(.01)
            self.report['final_off_frame_acknowledged']=bool(
                self.ack_at is not None and self.ack_at>=self.change_at and not self.ack_visible)
            self.stop.set();self.wake.set();self.thread.join(.2)
        if self.port is not None:self.port.close()
        self.report['link_error']=self.error
        self.report['sound']['pending_at_close']=len(self.sound_pending)

    def __exit__(self,*_):self.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--display-test',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if not args.display_test:
        print('No I/O. --display-test runs 20 seconds of DISPLAY ONLY; no motor access.')
        return 0
    if not args.output:parser.error('a new output file is required')
    with args.output.open('x') as output:
        report=dict(test='DISPLAY_ONLY',actuator_access=False)
        try:
            with CamIndicator(report) as indicator:
                print('DISPLAY_ONLY red on 15 s, then off 5 s; motors are not accessed.',flush=True)
                end=time.monotonic()+15.
                while time.monotonic()<end:indicator.tick();time.sleep(.02)
                indicator.deactivate()
                end=time.monotonic()+5.
                while time.monotonic()<end:indicator.check();time.sleep(.02)
            report['status']='PASS'
        except BaseException as exc:
            report.update(status='FAIL',reason=str(exc));raise
        finally:json.dump(report,output,indent=2)
    print(json.dumps(report),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
