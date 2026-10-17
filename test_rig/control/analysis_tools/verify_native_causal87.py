"""Frozen-input command-budget check; no devices or stability prediction."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from live_tuning import TuningChannel
from live_tuning_policy import gains
from protocol import RATIO,crc32_words
from two_deck_native_causal_balance import PLAN,NativeCausalBalanceController


def main():
    path=Path('logs/two-deck-balance-87-quiet-baseline.json')
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):digest.update(block)
    assert digest.hexdigest()=='3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285'
    raw=json.loads(path.read_text());c=NativeCausalBalanceController(TuningChannel(gains(PLAN)))
    n=limited=warmup=resets=0;maxff=maxnet=maxvelocity=0.;pid=None;begin=time.monotonic()
    for sample in raw['samples']:
        if 'cycle_work_ms' not in sample:continue
        a=copy.deepcopy(sample['attitude'])
        for key in ('wheel_position_forward_rad','wheel_feedback_received_monotonic'):
            a[key]={int(k):v for k,v in a[key].items()}
        speeds={int(k):v for k,v in a['ardupilot_balance']['wheel_rate_forward_rad_s'].items()}
        commands=c(a,speeds,PLAN)
        if pid is None:pid=c.pid
        assert pid is c.pid
        resets+=int(a['ardupilot_balance']['filter_reset'])
        warmup+=int(not a['velocity_frame_control']['ready'])
        limited+=int(a['ardupilot_balance']['adapter_limited'])
        for mid,sign in ((0,1),(1,-1)):
            p=c.allocated_torque_packet(mid,sign,commands[mid],PLAN)
            ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            assert pos==kp==0 and struct.unpack_from('<I',p,16)[0]==crc32_words(p[:16])
            wireff=sign*ff*RATIO/256000.;velocity=sign*v*6.283185307179586/(RATIO*2.56)
            damping=kd*RATIO**2/128000000.
            net=wireff+damping*(velocity-speeds[mid])
            assert abs(wireff)<=.12+1e-12 and abs(net)<=.12+1e-12 and abs(velocity)<=6.
            assert damping<=.040
            maxff=max(maxff,abs(wireff));maxnet=max(maxnet,abs(net));maxvelocity=max(maxvelocity,abs(velocity))
        n+=1
    assert resets==1
    result=dict(status='PASS',scope=__doc__,frames=n,raw_sha256=digest.hexdigest(),
        gains=gains(PLAN),native_kd_requested=.040,maximum_feedforward_nm=maxff,
        maximum_sampled_predicted_net_nm=maxnet,maximum_native_velocity_rad_s=maxvelocity,
        limited_frames=limited,warmup_frames=warmup,pid_identity_preserved=True,
        filter_resets=resets,analysis_wall_s=time.monotonic()-begin,
        limitation='Recorded trajectory came from a different controller. New commands were not applied; no prediction of actual NET torque, stability, floor motion, friction, backlash or settling.')
    with Path('logs/trial87-native-causal-budget.json').open('x') as out:
        json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
