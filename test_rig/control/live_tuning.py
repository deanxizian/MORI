"""Local, bounded gain mailbox and state-preserving live balance controller.

Socket parsing/writing runs in a worker. Only the control thread changes PID
state, at a sample boundary. Neither endpoint can enable/rearm a motor or
change any safety limit. A client disconnect leaves the last accepted gains;
the finite runner and every existing hardware guard remain authoritative.
"""
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import queue
import socket
import stat
import threading
import time
import uuid

from attitude import Fault
from live_tuning_policy import gains,with_gains,validate_set
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


SOCKET_PATH='/run/mori-balance-tune/control.sock'


class TuningChannel:
    def __init__(self,initial_gains,*,session=None,now=time.monotonic):
        self.session=session or uuid.uuid4().hex
        self.now=now;self.pending=queue.Queue(maxsize=1)
        self.disarm=threading.Event();self.failed=threading.Event()
        self.lock=threading.Lock()
        self.snapshot=dict(session=self.session,phase='WAITING',tuning_state='READY',
                           revision=0,current=initial_gains.copy(),target=initial_gains.copy(),
                           published_at=self.now(),last_window=None)

    def publish(self,snapshot):
        # Telemetry contention must never delay a motor pair.
        if not self.lock.acquire(blocking=False):return
        try:self.snapshot=dict(snapshot,session=self.session,published_at=self.now())
        finally:self.lock.release()

    def status(self):
        with self.lock:snapshot=self.snapshot
        result=copy.deepcopy(snapshot)
        if result['phase']=='ACTIVE' and self.now()-result['published_at']>.3:
            result['phase']='STALE'
        result['channel_failed']=self.failed.is_set()
        return result

    def submit(self,request):
        if type(request) is not dict:raise ValueError('object_required')
        if request=={'op':'status'}:return dict(status='PASS',state=self.status())
        state=self.status()
        if request.get('op')=='disarm':
            if set(request)!={'op','session'} or request['session']!=self.session:
                raise ValueError('wrong_disarm_session')
            self.disarm.set()
            return dict(status='DISARM_REQUESTED',session=self.session,
                        scope='Loop will stop and verify mode0; not physical power isolation')
        validate_set(request,self.session,state['revision'],state['current'])
        if self.failed.is_set() or self.disarm.is_set():raise ValueError('session_stopping')
        if state['phase']!='ACTIVE' or state['tuning_state']!='READY':
            raise ValueError('session_not_ready_for_tuning')
        try:self.pending.put_nowait(request.copy())
        except queue.Full as exc:raise ValueError('request_already_pending') from exc
        return dict(status='QUEUED',session=self.session,request_id=request['request_id'],
                    expected_revision=request['expected_revision'],
                    scope='Not yet applied; poll status for ramp/completion or rejection')

    def take(self):
        try:return self.pending.get_nowait()
        except queue.Empty:return None


def decode_request(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('duplicate_json_key')
            result[k]=v
        return result
    def constant(_):raise ValueError('nonfinite_json_number')
    return json.loads(raw.decode('utf8'),object_pairs_hook=pairs,parse_constant=constant)


class LocalTuningServer:
    def __init__(self,channel,path=SOCKET_PATH):
        self.channel=channel;self.path=Path(path);self.stop=threading.Event()
        self.listener=None;self.lockfile=None;self.thread=None;self.owns_socket=False

    def __enter__(self):
        try:
            self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            meta=self.path.parent.lstat()
            if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=os.geteuid() or meta.st_mode&0o077:
                raise ValueError('private_owned_socket_directory_required')
            fd=os.open(str(self.path)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            self.lockfile=os.fdopen(fd,'r+')
            fcntl.flock(self.lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
            # Only the lock owner can remove a socket left by a dead session.
            if self.path.exists():
                if not stat.S_ISSOCK(self.path.lstat().st_mode):raise ValueError('socket_path_is_not_socket')
                self.path.unlink()
            self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            self.listener.bind(str(self.path));self.owns_socket=True
            os.chmod(self.path,0o600);self.listener.listen(4);self.listener.settimeout(.1)
            self.thread=threading.Thread(target=self._serve,name='mori-gain-mailbox',daemon=True)
            self.thread.start();return self
        except BaseException:
            self.close();raise

    def _serve(self):
        try:
            while not self.stop.is_set():
                try:client,_=self.listener.accept()
                except socket.timeout:continue
                with client:
                    client.settimeout(.15)
                    try:
                        data=b''
                        while b'\n' not in data:
                            chunk=client.recv(4097-len(data))
                            if not chunk:raise ValueError('incomplete_request')
                            data+=chunk
                            if len(data)>4096:raise ValueError('request_too_large')
                        line,tail=data.split(b'\n',1)
                        if tail.strip():raise ValueError('one_request_per_connection')
                        response=self.channel.submit(decode_request(line))
                    except (ValueError,TypeError,KeyError,UnicodeError,OSError) as exc:
                        response=dict(status='REJECTED',reason=str(exc))
                    try:client.sendall((json.dumps(response,allow_nan=False)+'\n').encode())
                    except (OSError,socket.timeout):pass
        except BaseException:
            if not self.stop.is_set():self.channel.failed.set()
        finally:
            if not self.stop.is_set():self.channel.failed.set()

    def close(self):
        self.stop.set()
        if self.listener:self.listener.close()
        if self.thread:self.thread.join(timeout=.5)
        if self.owns_socket:
            self.path.unlink(missing_ok=True);self.owns_socket=False
        if self.lockfile:self.lockfile.close();self.lockfile=None

    def __exit__(self,*_):self.close()


class LiveTuningController(VelocityDiagnosticsController):
    def __init__(self,channel):
        self.channel=channel;self.ever_active=False
        super().__init__()

    def reset(self):
        if self.ever_active:raise Fault('live_controller_cannot_reset_after_active')
        super().reset()
        self.runtime_plan=None;self.source_plan=None;self.revision=0;self.ramp=None
        self.events=[];self.windows=[];self.seen=set();self.last_result=None
        self.active_start=None;self.ready_at=None;self.last_publish=-math.inf
        self.window=None;self.finish_reason=None;self.last_telemetry={}

    def check_external_stop(self):
        if self.channel.disarm.is_set():raise Fault('operator_disarm_requested')
        if self.channel.failed.is_set():raise Fault('live_tuning_channel_failed')

    def validate_arm(self,attitude,speeds,plan):
        self.check_external_stop()
        # No request admission or live state is started during zero arm.
        return super().__call__(attitude,speeds,plan)

    def _event(self,event):
        self.events.append(event);self.events=self.events[-256:]
        self.last_result=event.copy()

    def __call__(self,attitude,speeds,plan):
        self.check_external_stop();t=attitude['t']
        if self.runtime_plan is None:
            maximum=1800 if plan.get('half_hour_live_session') is True else 600
            if plan.get('allow_live_tuning') is not True or not 0<plan['duration_s']<=maximum:
                raise Fault('invalid_live_tuning_plan')
            self.source_plan=plan.copy();self.runtime_plan=with_gains(plan,gains(plan))
            self.active_start=t;self.ready_at=t+5.;self.ever_active=True
        elif plan!=self.source_plan:raise Fault('live_source_plan_changed')
        request=self.channel.take()
        if request is not None:
            try:
                current=gains(self.runtime_plan)
                key,value,duration=validate_set(request,self.channel.session,self.revision,current)
                if request['request_id'] in self.seen:raise ValueError('duplicate_request_id')
                if len(self.seen)>=64:raise ValueError('session_update_limit')
                if self.ramp is not None or t<self.ready_at:raise ValueError('settling_or_ramping')
                if abs(attitude['pitch_deg'])>5 or max(abs(v) for v in speeds.values())>3 or self.previous_limited:
                    raise ValueError('outside_tuning_window_keep_previous_gains')
                target=dict(current,**{key:value});self.revision+=1
                self.seen.add(request['request_id'])
                self.ramp=dict(start=t,duration=duration,before=current,target=target,
                               request_id=request['request_id'])
                self.window=None
                self._event(dict(status='RAMP_STARTED',revision=self.revision,t=t,
                                 request_id=request['request_id'],before=current,target=target))
            except (ValueError,KeyError,TypeError) as exc:
                self._event(dict(status='REJECTED',revision=self.revision,t=t,
                                 request_id=request.get('request_id'),reason=str(exc)))
        if self.ramp is not None:
            ramp=self.ramp;fraction=min(1.,max(0.,(t-ramp['start'])/ramp['duration']))
            values={k:ramp['before'][k]+fraction*(ramp['target'][k]-ramp['before'][k]) for k in ramp['before']}
            updated=with_gains(self.runtime_plan,values)
            self.apply_live_gains(self.runtime_plan,updated);self.runtime_plan=updated
            if fraction>=1:
                self._event(dict(status='APPLIED',revision=self.revision,t=t,
                                 request_id=ramp['request_id'],current=values.copy()))
                self.ready_at=t+2.;self.ramp=None
        commands=super().__call__(attitude,speeds,self.runtime_plan)
        state='RAMPING' if self.ramp else ('SETTLING' if t<self.ready_at else 'READY')
        attitude['live_tuning']=dict(revision=self.revision,state=state,current=gains(self.runtime_plan))
        return commands

    def observe_pair(self,sample):
        a=sample['attitude'];t=a['t'];info=a['live_tuning']
        feedback=[w['feedback'] for w in sample['wheels'].values()]
        pos=sum(sample['rolling_equivalent']['forward_offset_m'].values())/2
        self.last_telemetry=dict(pitch_deg=a['pitch_deg'],pitch_rate_dps=a['pitch_rate_dps'],
             temperature_c=[f['temperature_c'] for f in feedback],
             max_shaft_speed_rad_s=max(abs(f['speed_rad_s']) for f in feedback),
             common_encoder_offset_m=pos,active_elapsed_s=t-self.active_start)
        if hasattr(self,'extra_telemetry'):
            extra=self.extra_telemetry(sample)
            if set(extra)&set(self.last_telemetry):raise Fault('telemetry_extension_overrides_guard_fields')
            self.last_telemetry.update(extra)
        if info['state']=='READY':
            v=a['velocity_hold']['encoder_velocity_proxy_m_s']
            if self.window is None:
                self.window=dict(start=t,n=0,lo=pos,hi=pos,pitch2=0.,speed2=0.,rate2=0.,limited=0)
            w=self.window;w['n']+=1;w['lo']=min(w['lo'],pos);w['hi']=max(w['hi'],pos)
            w['pitch2']+=a['pitch_deg']**2;w['speed2']+=v*v;w['rate2']+=a['pitch_rate_dps']**2
            w['limited']+=bool(a['ardupilot_balance']['adapter_limited'])
            if t-w['start']>=10:
                self.windows.append(dict(revision=self.revision,gains=info['current'].copy(),
                    start_elapsed_s=w['start']-self.active_start,end_elapsed_s=t-self.active_start,
                    samples=w['n'],common_encoder_span_m=w['hi']-w['lo'],
                    pitch_rms_deg=math.sqrt(w['pitch2']/w['n']),
                    encoder_velocity_rms_m_s=math.sqrt(w['speed2']/w['n']),
                    pitch_rate_rms_dps=math.sqrt(w['rate2']/w['n']),adapter_limited_frames=w['limited']))
                keep=192 if self.source_plan.get('half_hour_live_session') is True else 64
                self.windows=self.windows[-keep:];self.window=None
        if t-self.last_publish>=.1:
            self.last_publish=t
            self.channel.publish(dict(phase='ACTIVE',tuning_state=info['state'],revision=self.revision,
                current=info['current'].copy(),target=(self.ramp['target'].copy() if self.ramp else info['current'].copy()),
                last_result=copy.deepcopy(self.last_result),last_window=(self.windows[-1].copy() if self.windows else None),
                completed_windows=[w.copy() for w in self.windows],**self.last_telemetry))

    def finish(self):self.finish_reason='duration_elapsed'

    def summary(self):
        result=dict(session=self.channel.session,revision=self.revision,
                    current=gains(self.runtime_plan) if self.runtime_plan else None,
                    events=copy.deepcopy(self.events),windows=copy.deepcopy(self.windows),
                    finish_reason=self.finish_reason or 'runner_stopped_see_report_reason',
                    pending_request_cancelled=self.channel.take(),automatic_rearm=False)
        self.channel.publish(dict(phase='STOPPED',tuning_state='STOPPED',revision=self.revision,
                                  current=result['current'],target=result['current'],last_result=self.last_result,
                                  last_window=(self.windows[-1].copy() if self.windows else None),**self.last_telemetry))
        return result
