"""Recorded-input check, not a closed-loop simulation or robot validation."""
import copy,hashlib,json,pathlib,subprocess,sys

base=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base))
from two_deck_pitch325_speed030 import PLAN
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

changed=sorted(k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k))
assert changed==['active_message','control_phase','name','speed_kp_rad_per_m_s'],changed
p=subprocess.run([sys.executable,str(base/'two_deck_pitch325_speed030.py')],capture_output=True,text=True,check=True)
assert json.loads(p.stdout)['hardware_opened'] is False
raw=(base/'logs/two-deck-balance-71-pitch325-observe.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c64fa4451acb139a08da24aebb75465c557cf2bfc3dfcc8c7dc4e6cc94647ab1'
data=json.loads(raw)
stats=[]
for label,plan in [('baseline',BASE),('candidate',PLAN)]:
    controller=VelocityDiagnosticsController()
    maximum_ff=maximum_net=maximum_replay_error=0.
    limited=0
    for sample in data['samples']:
        attitude=copy.deepcopy(sample['attitude'])
        for key in ('wheel_position_forward_rad','wheel_feedback_received_monotonic'):
            attitude[key]={int(k):v for k,v in attitude[key].items()}
        speeds={int(k):v for k,v in sample['attitude']['ardupilot_balance']['wheel_rate_forward_rad_s'].items()}
        commands=controller(attitude,speeds,plan)
        info=attitude['ardupilot_balance']
        for mid,command in commands.items():
            packet=controller.allocated_torque_packet(mid,1 if mid==0 else -1,command,plan)
            assert len(packet)==20
            maximum_ff=max(maximum_ff,abs(command))
            maximum_net=max(maximum_net,abs(info['predicted_net_forward_nm'][mid]))
            if label=='baseline':
                prior=sample['attitude']['ardupilot_balance']['command_forward_nm'][str(mid)]
                maximum_replay_error=max(maximum_replay_error,abs(command-prior))
        limited+=info['adapter_limited']
    assert maximum_ff<=.12+1e-12 and maximum_net<=.12+1e-12
    if label=='baseline':assert maximum_replay_error<1e-12,maximum_replay_error
    stats.append(dict(controller=label,frames=len(data['samples']),max_ff_nm=maximum_ff,
                      max_net_nm=maximum_net,limited_frames=limited,
                      baseline_command_max_error_nm=maximum_replay_error if label=='baseline' else None))
print(json.dumps(dict(status='PASS',changed_fields=changed,inert_default=True,
    input_sha256=hashlib.sha256(raw).hexdigest(),results=stats,
    scope='Frozen recorded inputs and command budgets only. No closed-loop outcome prediction.'),indent=2))
