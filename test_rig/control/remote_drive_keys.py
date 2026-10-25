"""Pinned Xiaomi evdev input. No motor, tuning or enable API imports.

Single worker publishes immutable tuples; the CPython control reader never
waits on a lock or does I/O. Kernel repeats are NOT wireless heartbeats.
The operator requests continuous hold: fresh key state remains active until
release. A stale worker, disconnect or dropped input produces neutral.
Reattachment still requires release; repeats cannot manufacture a keydown.
"""
import select,subprocess,threading,time
ADDRESS='c0:5d:39:c3:60:ae'
ARROWS={103,108,105,106};STOPS={28,158}
LEASE=.15
LINK_LEASE=.8

class Keys:
    def __init__(self):
        self.held=set();self.since={};self.blocked=True;self.connected=False
        self.value=(0.,False,True,0,0,0,'not_connected')
        self.diagnostics={'phase':'not_started'}
    def attach(self,now,held):
        self.connected=True;self.held=set(held);self.since={};self.blocked=True
        self.publish(now)
    def disconnect(self,now):
        self.connected=False;self.blocked=True;self.held=set();self.since={};self.publish(now)
    def event(self,code,value,now):
        if code not in ARROWS|STOPS:return
        if value==0:self.held.discard(code);self.since.pop(code,None)
        elif value==1:
            self.held.add(code)
            if code not in self.since:self.since[code]=now
            if code in STOPS:self.blocked=True
        # Repeats do not renew a press or manufacture a missing keydown.
    def publish(self,now,active=None):
        if active is not None:
            relevant=set(active)&(ARROWS|STOPS)
            if relevant-self.held:self.blocked=True
            self.held=relevant;self.since={k:v for k,v in self.since.items() if k in relevant}
        if not self.held:self.blocked=False;self.since={}
        if self.held&STOPS:self.blocked=True
        allowed=self.connected and not self.blocked
        forward=int(103 in self.held)-int(108 in self.held) if allowed else 0
        right=int(106 in self.held)-int(105 in self.held) if allowed else 0
        mask=sum(1<<i for i,k in enumerate(sorted(ARROWS|STOPS)) if k in self.held)
        reason='ready' if allowed else ('release_required' if self.connected else 'not_connected')
        self.value=(now,self.connected,self.blocked,mask,forward,right,reason)
        return self.value
    def read(self,now):
        row=self.value
        # IMU completion may precede a concurrent publication by one frame.
        if not -.025<=now-row[0]<=LEASE:return (now,False,True,row[3],0,0,'input_stale')
        return row

class LinkProbe:
    """Slow BlueZ checks never block the evdev heartbeat; failures are neutral."""
    def __init__(self,stop,query=None,now=time.monotonic):
        self.stop=stop;self.now=now;self.query=query or self.query_bluez
        self.value=(0.,False,'not_checked');self.errors=0;self.last_error=None
    @staticmethod
    def query_bluez():
        p=subprocess.run(['bluetoothctl','info',ADDRESS],capture_output=True,text=True,timeout=.3)
        return p.returncode==0 and 'Connected: yes' in p.stdout
    def sample_once(self):
        try:connected=bool(self.query());error=None
        except Exception as e:
            connected=False;error=type(e).__name__+': '+str(e);self.errors+=1;self.last_error=error
        self.value=(self.now(),connected,error)
        return self.value
    def read(self,now):
        timestamp,connected,error=self.value
        return bool(connected and 0<=now-timestamp<=LINK_LEASE),error
    def run(self):
        while not self.stop.is_set():
            begin=self.now();self.sample_once()
            self.stop.wait(max(0.,.5-(self.now()-begin)))

class KeyWorker:
    def __init__(self,keys,report):
        self.keys=keys;self.report=report;self.stop=threading.Event();self.thread=None
        self.link_probe=LinkProbe(self.stop)
    def __enter__(self):
        self.thread=threading.Thread(target=self.run,name='remote-keys',daemon=True);self.thread.start();return self
    def __exit__(self,*_):
        self.stop.set()
        if self.thread:self.thread.join(2.)
        self.keys.disconnect(time.monotonic())
    def diagnostic(self,phase,**extra):
        self.report.update(phase=phase,**extra)
        self.keys.diagnostics=self.report.copy()
    @staticmethod
    def close_device(d):
        if d is not None:
            try:d.close()
            except OSError:pass
    def consume_device(self,d,now):
        # EAGAIN after select is a normal nonblocking race, not link loss.
        ready,_,_=select.select([d],[],[],.02)
        if ready:
            try:events=d.read()
            except BlockingIOError:events=()
            for e in events:
                if e.type==0 and e.code==3:  # EV_SYN/SYN_DROPPED
                    self.keys.blocked=True;self.keys.since={}
                elif e.type==1:self.keys.event(e.code,e.value,time.monotonic())
        self.keys.publish(time.monotonic(),d.active_keys())
    def run(self):
        import os
        try:
            os.sched_setscheduler(0,os.SCHED_OTHER,os.sched_param(0))
            os.sched_setaffinity(0,{0,1});os.setpriority(os.PRIO_PROCESS,0,10)
        except OSError as e:
            self.keys.disconnect(time.monotonic());self.diagnostic('profile_failed',worker_profile_error=str(e));return
        import evdev
        d=None;next_scan=0.;errors=0
        # Created after demotion: this worker inherits OTHER/nice10/CPU0,1.
        link_thread=threading.Thread(target=self.link_probe.run,name='remote-link',daemon=True)
        link_thread.start()
        try:
            while not self.stop.is_set():
                now=time.monotonic();link,error=self.link_probe.read(now)
                if not link:
                    self.close_device(d);d=None;self.keys.disconnect(now)
                    self.diagnostic('waiting_link',link_error=error,link_errors=self.link_probe.errors,last_link_error=self.link_probe.last_error)
                    self.stop.wait(.02);continue
                try:
                    if d is None and now>=next_scan:
                        for path in evdev.list_devices():
                            try:x=evdev.InputDevice(path)
                            except OSError:continue
                            if (x.uniq or '').lower()!=ADDRESS:x.close();continue
                            try:x.grab();held=x.active_keys()
                            except Exception:
                                self.close_device(x);raise
                            d=x;self.keys.attach(time.monotonic(),held)
                            self.report.update(path=d.path,identity=d.uniq,name=d.name);break
                        next_scan=now+.5
                    if d is None:
                        self.keys.disconnect(now);self.diagnostic('waiting_device');self.stop.wait(.03);continue
                    self.consume_device(d,now)
                    self.diagnostic('reading',link_error=error,link_errors=self.link_probe.errors,last_link_error=self.link_probe.last_error,input_errors=errors)
                except Exception as e:
                    # A transient ioctl/device/select failure cannot permanently
                    # kill input. Drop intent and require release on reattach.
                    errors+=1;self.keys.disconnect(time.monotonic());self.close_device(d);d=None
                    self.diagnostic('recovering_device',input_errors=errors,last_input_error=type(e).__name__+': '+str(e))
                    next_scan=time.monotonic()+.2;self.stop.wait(.05)
        finally:
            self.stop.set();link_thread.join(1.)
            self.keys.disconnect(time.monotonic());self.close_device(d);self.diagnostic('stopped')
