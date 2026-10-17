"""Counterfactual frozen command-budget check; no device access or stability proof."""
import copy,hashlib,json,struct,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from live_tuning import TuningChannel
from live_tuning_policy import gains
from protocol import crc32_words
from two_deck_live_causal_velocity import PLAN,CausalVelocityLiveController


def main():
    p=Path('logs/two-deck-balance-87-quiet-baseline.json');digest=hashlib.sha256()
    with p.open('rb') as f:
        for q in iter(lambda:f.read(4*1024*1024),b''):digest.update(q)
    assert digest.hexdigest()=='3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285'
    raw=json.loads(p.read_text());c=CausalVelocityLiveController(TuningChannel(gains(PLAN)))
    n=limited=warmup=0;maxff=maxnet=0.;pid=None;reset_count=0;begin=time.monotonic()
    for s in raw['samples']:
        if 'cycle_work_ms' not in s:continue
        a=copy.deepcopy(s['attitude'])
        for key in ('wheel_position_forward_rad','wheel_feedback_received_monotonic'):
            a[key]={int(k):v for k,v in a[key].items()}
        speeds={int(k):v for k,v in a['ardupilot_balance']['wheel_rate_forward_rad_s'].items()}
        commands=c(a,speeds,PLAN)
        if pid is None:pid=c.pid
        assert pid is c.pid
        reset_count+=int(a['ardupilot_balance']['filter_reset'])
        warmup+=int(not a['velocity_frame_control']['ready'])
        limited+=int(a['ardupilot_balance']['adapter_limited'])
        for mid,sign in ((0,1),(1,-1)):
            packet=c.allocated_torque_packet(mid,sign,commands[mid],PLAN)
            ff,v,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
            assert (v,pos,kp)==(0,0,0)
            assert struct.unpack_from('<I',packet,16)[0]==crc32_words(packet[:16])
            allocation=c.allocations[mid]
            maxff=max(maxff,abs(allocation.feedforward_nm));maxnet=max(maxnet,abs(allocation.predicted_net_nm))
            assert abs(allocation.feedforward_nm)<=.12+1e-12 and abs(allocation.predicted_net_nm)<=.12+1e-12
        n+=1
    assert reset_count==1
    result=dict(status='PASS',scope=__doc__,raw_sha256=digest.hexdigest(),frames=n,
        candidate_gains=gains(PLAN),warmup_frames=warmup,limited_frames=limited,
        maximum_feedforward_nm=maxff,maximum_predicted_net_nm=maxnet,
        pid_identity_preserved=True,filter_resets=reset_count,
        execution_wall_s=time.monotonic()-begin,
        limitations='Recorded input trajectory was produced by another controller. New commands were never applied. No prediction of physical stability, settling, disturbance recovery, accuracy or friction. This check is local only; trial90 remains unchanged.')
    with Path('logs/trial87-causal-command-budget.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
