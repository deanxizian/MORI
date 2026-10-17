"""Recorded input, protocol budget and state-continuity replay; no plant simulation."""
import copy
import gc
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base))
from live_tuning import LiveTuningController,TuningChannel
from live_tuning_policy import gains
from two_deck_live_tuning import PLAN

raw=(base/'logs/two-deck-balance-71-pitch325-observe.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c64fa4451acb139a08da24aebb75465c557cf2bfc3dfcc8c7dc4e6cc94647ab1'
record=json.loads(raw);results=[]
enabled=gc.isenabled();gc.disable()
try:
    for online in (False,True):
        clock=[0.];ch=TuningChannel(gains(PLAN),session='recorded-input',now=lambda:clock[0])
        controller=LiveTuningController(ch);pid=None;maximum_ff=maximum_net=maximum_error=0.;work=[]
        targets=[(10.,'pitch_p',3.),(20.,'pitch_i',.45),(30.,'pitch_d',.08),(40.,'speed_p',.20)] if online else []
        for row in record['samples']:
            a=copy.deepcopy(row['attitude']);clock[0]=a['t']
            for k in ('wheel_position_forward_rad','wheel_feedback_received_monotonic'):
                a[k]={int(mid):v for mid,v in a[k].items()}
            speeds={int(k):v for k,v in row['attitude']['ardupilot_balance']['wheel_rate_forward_rad_s'].items()}
            if targets and row['elapsed_s']>=targets[0][0]:
                _,key,value=targets.pop(0)
                response=ch.submit(dict(op='set',session=ch.session,expected_revision=controller.revision,
                    request_id=key,key=key,value=value,ramp_s=2.))
                assert response['status']=='QUEUED'
            start=time.perf_counter()
            commands=controller(a,speeds,PLAN)
            if pid is None:pid=controller.pid
            assert controller.pid is pid
            for mid,command in commands.items():
                packet=controller.allocated_torque_packet(mid,1 if mid==0 else -1,command,PLAN)
                assert len(packet)==20 and packet[2]&0x70==0x10
                maximum_ff=max(maximum_ff,abs(command))
                maximum_net=max(maximum_net,abs(a['ardupilot_balance']['predicted_net_forward_nm'][mid]))
                if not online:
                    maximum_error=max(maximum_error,abs(command-row['attitude']['ardupilot_balance']['command_forward_nm'][str(mid)]))
            checked=dict(row,attitude=a);controller.observe_pair(checked)
            work.append((time.perf_counter()-start)*1000)
        assert maximum_ff<=.12+1e-12 and maximum_net<=.12+1e-12
        if not online:assert maximum_error<1e-12
        events=controller.summary()['events']
        if online:assert [x['status'] for x in events]==['RAMP_STARTED','APPLIED']*4,events
        ordered=sorted(work)
        results.append(dict(online_updates=online,frames=len(record['samples']),
            maximum_ff_nm=maximum_ff,maximum_net_nm=maximum_net,
            baseline_command_max_error_nm=maximum_error if not online else None,
            same_pid_object=True,events=events,control_math_plus_telemetry_ms=dict(
                mean=statistics.mean(work),p99=ordered[int(.99*(len(ordered)-1))],maximum=max(work))))
finally:
    if enabled:gc.enable()
print(json.dumps(dict(status='PASS',input_sha256=hashlib.sha256(raw).hexdigest(),results=results,
    scope='Frozen observed inputs, gain state continuity and wire budgets only. Timing excludes sensor/USB and is not a Linux deadline guarantee. No closed-loop prediction.'),indent=2))
