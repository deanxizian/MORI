#!/usr/bin/env python3
"""Finite BMI323 / dual S288 timing probe. Only disabled-mode packets exist.

No arguments means zero hardware I/O. This is not a balancing controller.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
import math
from pathlib import Path
import signal
import statistics
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
PORT = '/dev/serial/by-id/usb-Artery_AT32_Virtual_Com_Port_366DCBC91974-if00'
sys.path.insert(0, str(HERE/'bench_support'))
from protocol import locked_query


class CycleGC:
    """Attribute GC pauses or defer cyclic GC during this bounded capture.

    Reference counting remains enabled; this is not a realtime guarantee.
    Restore the caller's state and remove the callback on every exit.
    """
    def __init__(self, report, policy):
        self.report,self.policy=report,policy
        self.enabled=gc.isenabled()
        self.started={}

    def callback(self,phase,info):
        generation=info['generation']
        now=time.monotonic()
        if phase=='start':
            self.started[generation]=now
        elif generation in self.started:
            begin=self.started.pop(generation)
            self.report['events'].append(dict(start=begin,end=now,generation=generation,
                                               duration_ms=(now-begin)*1000))

    def __enter__(self):
        self.report.update(policy=self.policy,previously_enabled=self.enabled,events=[])
        if self.policy=='defer':
            gc.collect()
            gc.disable()
        gc.callbacks.append(self.callback)
        return self

    def __exit__(self,*_):
        gc.callbacks.remove(self.callback)
        if self.enabled:
            gc.enable()
        else:
            gc.disable()
        self.report['state_restored']=gc.isenabled()==self.enabled


def stats(values):
    if not values:
        return None
    s = sorted(values)
    return dict(n=len(s), minimum=s[0], mean=statistics.mean(s),
                p50=s[int((len(s)-1)*.5)], p99=s[int((len(s)-1)*.99)], maximum=s[-1])


def decode(words):
    if len(words) != 7:
        raise ValueError('invalid_imu_length')
    raw = [w if w < 32768 else w-65536 for w in words]
    if any(abs(w) >= 32700 for w in raw[:6]) or raw[6] == -32768:
        raise ValueError('invalid_or_saturated_imu')
    return dict(raw=raw, accel_g=[v/8192 for v in raw[:3]],
                gyro_dps=[v/32.768 for v in raw[3:6]], temperature_c=raw[6]/512+23)


class RawIMU:
    def __init__(self, report, *, bandwidth_divisor=2, odr_hz=100):
        # Bosch BST-BMI323-DS000-13: ACC_CONF/GYR_CONF bit 7 selects
        # ODR/2 or ODR/4 in normal mode. Ranges and scaling stay fixed;
        # explicit100/200Hz ODR changes only low bits8/9 (Bosch ACC/GYR_CONF).
        if type(bandwidth_divisor) is not int or bandwidth_divisor not in (2,4):
            raise ValueError('unsupported_imu_bandwidth_divisor')
        if type(odr_hz) is not int or odr_hz not in (100,200):
            raise ValueError('unsupported_imu_odr')
        bit=0x80 if bandwidth_divisor==4 else 0
        odr=8 if odr_hz==100 else 9
        self.requested_config={0x20:0x4010|bit|odr,0x21:0x4030|bit|odr}
        self.report, self.bus, self.lock, self.saved = report, None, None, {}
        self.report.update(odr_hz=odr_hz,bandwidth_divisor=bandwidth_divisor,
                           bandwidth_setting='ODR/'+str(bandwidth_divisor))
        self.changed = False

    def read(self, reg, n=1):
        from smbus2 import i2c_msg
        r = i2c_msg.read(0x69, 2+2*n)
        self.bus.i2c_rdwr(i2c_msg.write(0x69, [reg]), r)
        return struct.unpack('<'+'H'*n, bytes(r)[2:])

    def write(self, reg, value):
        from smbus2 import i2c_msg
        self.bus.i2c_rdwr(i2c_msg.write(0x69, bytes([reg])+struct.pack('<H', value)))
        time.sleep(.001)

    def __enter__(self):
        from smbus2 import SMBus
        try:
            self.lock = open('/run/lock/mori-bmi323-demo.lock', 'a')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.bus = SMBus(1)
            ids = [self.read(0)[0] & 255 for _ in range(3)]
            self.report['chip_ids'] = ids
            if ids != [0x43]*3 or self.read(1)[0]:
                raise RuntimeError('imu_identity_or_error')
            self.saved = {r:self.read(r)[0] for r in (0x20, 0x21)}
            self.report['config_before'] = self.saved
            if any(v & 0x7000 for v in self.saved.values()):
                raise RuntimeError('refuse_active_sensor')
            self.changed = True
            for reg, value in self.requested_config.items():
                self.write(reg, value)
            self.report['config_during'] = {r:self.read(r)[0] for r in self.saved}
            if self.report['config_during'] != self.requested_config:
                raise RuntimeError('imu_readback_mismatch')
            time.sleep(.2)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def sample(self):
        begin = time.monotonic()
        while self.read(2)[0] & 0xc0 != 0xc0:
            if time.monotonic()-begin > .03:
                raise RuntimeError('imu_data_ready_timeout_30ms')
            time.sleep(.0005)
        return self._read_sample(begin)

    def sample_nowait(self):
        """Read at most one ready frame; never wait for the next sensor frame.

        Intended for passive stop observation AFTER both lock packets were
        attempted. I2C system-call latency is still not a realtime guarantee.
        """
        begin = time.monotonic()
        if self.read(2)[0] & 0xc0 != 0xc0:
            return None
        return self._read_sample(begin)

    def _read_sample(self, begin):
        words = self.read(3, 7)
        end = time.monotonic()
        self.last_rejected_sample = None
        try:
            values = decode(words)
        except Exception as exc:
            self.last_rejected_sample = dict(t_read_complete=end,
                raw_words=list(words), reason=str(exc))
            raise
        return dict(t_read_complete=end, read_wait_ms=(end-begin)*1000, **values)

    def __exit__(self, *_):
        errors = []
        if self.changed:
            for reg,value in self.saved.items():
                try:
                    self.write(reg,value)
                except Exception as exc:
                    errors.append(str(exc))
            try:
                restored = {r:self.read(r)[0] for r in self.saved}
                self.report['config_after'] = restored
                self.report['configuration_restored'] = restored == self.saved
                if restored != self.saved:
                    errors.append('imu_restore_mismatch')
            except Exception as exc:
                errors.append(str(exc))
        if self.bus:
            self.bus.close()
        if self.lock:
            self.lock.close()
        if errors:
            self.report['restore_errors'] = errors
            raise RuntimeError('imu_restore_failed')


def disabled_exchange(exchange, mid, phase):
    # The only emitted packet is the pinned mode-0/zero-target builder.
    row = exchange(locked_query(mid), phase)
    if row['mode'] != 0:
        raise RuntimeError('servo_not_in_disabled_mode')
    if not math.isfinite(row['speed_rad_s']) or abs(row['speed_rad_s']) > .04:
        raise RuntimeError('unexpected_wheel_motion')
    if row['errors_raw'] or row['warning_raw']:
        raise RuntimeError('servo_error_or_warning')
    return row


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--measure', action='store_true')
    p.add_argument('--seconds', type=int, default=20, choices=range(1,121))
    p.add_argument('--hz', type=int, choices=(50,100,200), default=100)
    p.add_argument('--imu-odr-hz', type=int, choices=(100,200), default=100)
    p.add_argument('--imu-bandwidth-divisor', type=int, choices=(2,4), default=2)
    p.add_argument('--port')
    p.add_argument('--output', type=Path)
    p.add_argument('--gc-policy', choices=('observe','defer'), default='observe')
    args = p.parse_args(argv)
    if not args.measure:
        print(json.dumps(dict(status='NOT_TESTED', hardware_opened=False,
                              motor_enable_commands=0, purpose='disabled timing and raw IMU only')))
        return 0
    if args.hz>args.imu_odr_hz:
        p.error('capture_rate_cannot_exceed_imu_odr')
    if args.port != PORT or not args.output or sys.platform != 'linux':
        p.error('Linux Pi, exact Unitree by-id port and new output path required')
    import bench
    from jog_once import serial_exchange
    manifest = json.loads((HERE/'bench_support/manifest.json').read_text())
    for name,h in manifest['sha256'].items():
        if hashlib.sha256((HERE/'bench_support'/name).read_bytes()).hexdigest() != h:
            raise RuntimeError('support_source_mismatch')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    report = dict(utc=datetime.now(timezone.utc).isoformat(), status='FAIL',
                  requested_hz=args.hz, requested_imu_odr_hz=args.imu_odr_hz,
                  requested_seconds=args.seconds, imu={}, samples=[],
                  per_id={mid:dict(transactions=[]) for mid in (0,1)},
                  motor_enable_commands=0, timeout_clear_commands=0,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),gc={},
                  timestamp_boundary='host read completion; not sensor hardware capture timestamp')
    interrupted = False
    def stop(sig, _):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt('signal_'+str(sig))
    handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
    with args.output.open('x') as output:
        try:
            with ExitStack() as stack:
                stack.enter_context(CycleGC(report['gc'],args.gc_policy))
                imu_options={}
                if args.imu_odr_hz!=100:imu_options['odr_hz']=args.imu_odr_hz
                if args.imu_bandwidth_divisor!=2:imu_options['bandwidth_divisor']=args.imu_bandwidth_divisor
                imu = stack.enter_context(RawIMU(report['imu'],**imu_options))
                record = bench.select_port(bench.port_records(),args.port)
                report['selected_port'] = record
                port = stack.enter_context(bench.open_port(record))
                port.timeout,port.write_timeout = .001,.02
                exchanges = {mid:serial_exchange(port,mid,report['per_id'][mid]) for mid in (0,1)}
                try:
                    for mid in (0,1):
                        disabled_exchange(exchanges[mid],mid,'preflight_disabled')
                    begin = previous = time.monotonic()
                    deadline,last_print = begin,begin-10
                    print('DISABLED_CAPTURE_READY: 电机保持 mode 0，正在采集原始 IMU 与通信时序。',flush=True)
                    while time.monotonic()-begin < args.seconds:
                        tick=time.monotonic()
                        sample=imu.sample()
                        wheels={mid:disabled_exchange(exchanges[mid],mid,'disabled_measure') for mid in (0,1)}
                        end=time.monotonic()
                        report['samples'].append(dict(t=tick,elapsed_s=tick-begin,frame_gap_ms=(tick-previous)*1000,
                            cycle_work_ms=(end-tick)*1000,imu_age_at_end_ms=(end-sample['t_read_complete'])*1000,
                            imu=sample,wheels=wheels))
                        previous=tick
                        if tick-last_print>=5:
                            print(json.dumps(dict(elapsed_s=round(tick-begin,1),samples=len(report['samples']),
                                accel_g=[round(v,3) for v in sample['accel_g']],
                                gyro_dps=[round(v,2) for v in sample['gyro_dps']],
                                temperature_c=[wheels[mid]['temperature_c'] for mid in (0,1)])),flush=True)
                            last_print=tick
                        deadline+=1/args.hz
                        if end>deadline:
                            deadline=end
                        time.sleep(max(0,deadline-time.monotonic()))
                    report['status']='PASS'
                    report['elapsed_s']=time.monotonic()-begin
                finally:
                    good={mid:0 for mid in (0,1)}
                    for _ in range(3):
                        time.sleep(.02)
                        for mid in (0,1):
                            try:
                                disabled_exchange(exchanges[mid],mid,'final_disabled')
                                good[mid]+=1
                            except Exception as exc:
                                report.setdefault('stop_errors',[]).append(dict(id=mid,error=str(exc)))
                    report['final_disabled_verified']=all(n==3 for n in good.values())
                    if not report['final_disabled_verified']:
                        report.update(status='FAIL',physical_power_cut_required=True)
        except (Exception,KeyboardInterrupt) as exc:
            report.update(status='FAIL',reason=str(exc) or type(exc).__name__)
        finally:
            s=report['samples']
            report['timing']=dict(frame_gap_ms=stats([r['frame_gap_ms'] for r in s[1:]]),
                cycle_work_ms=stats([r['cycle_work_ms'] for r in s]),
                imu_age_at_end_ms=stats([r['imu_age_at_end_ms'] for r in s]))
            report['motor_commands_sent']=sum(len(r['transactions']) for r in report['per_id'].values())
            json.dump(report,output,indent=2)
            for sig,handler in handlers.items():
                signal.signal(sig,handler)
    print(json.dumps({k:report.get(k) for k in ('status','reason','elapsed_s','motor_commands_sent',
        'motor_enable_commands','final_disabled_verified','timing')},indent=2,ensure_ascii=False),flush=True)
    return 0 if report['status']=='PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
