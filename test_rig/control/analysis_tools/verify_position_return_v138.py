"""Recorded-input parity and bounds check; not a closed-loop simulation."""
import copy
import hashlib
import json
import pathlib
import subprocess
import sys

BASE_DIR=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE_DIR))
from two_deck_trim_position_return import PLAN
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_position_hold import PositionHoldController
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


def main():
    changed=sorted(k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k))
    assert changed==['active_message','allow_position_velocity_target','control_phase','name',
                     'position_speed_kp_per_s','position_speed_limit_m_s'],changed
    inert=subprocess.run([sys.executable,str(BASE_DIR/'two_deck_trim_position_return.py')],
                         capture_output=True,text=True,check=True)
    assert json.loads(inert.stdout)['hardware_opened'] is False
    raw=(BASE_DIR/'logs/two-deck-balance-66-baseline-audio.json').read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    assert digest=='d3640daa934d9cbc893554b938770d7f773445863e31d29da836a70bf7c06361'
    data=json.loads(raw)
    results=[]
    for label,plan,controller in [('baseline',BASE,VelocityDiagnosticsController()),
                                  ('candidate',PLAN,PositionHoldController())]:
        max_ff=max_net=max_replay_error=max_target=0.
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
                max_ff=max(max_ff,abs(command))
                max_net=max(max_net,abs(info['predicted_net_forward_nm'][mid]))
                if label=='baseline':
                    prior=sample['attitude']['ardupilot_balance']['command_forward_nm'][str(mid)]
                    max_replay_error=max(max_replay_error,abs(command-prior))
            if label=='candidate':
                pos=attitude['position_hold']
                assert pos['relative_error_proxy_m']*pos['target_velocity_m_s']<=0
                max_target=max(max_target,abs(pos['target_velocity_m_s']))
            limited+=info['adapter_limited']
        assert max_ff<=.12+1e-12 and max_net<=.12+1e-12
        assert max_target<=.01+1e-12
        if label=='baseline':assert max_replay_error<1e-12,max_replay_error
        results.append(dict(controller=label,frames=len(data['samples']),max_ff_nm=max_ff,
                            max_net_nm=max_net,limited_frames=limited,
                            max_position_return_speed_target_m_s=max_target,
                            baseline_command_max_error_nm=max_replay_error if label=='baseline' else None))
    print(json.dumps(dict(status='PASS',changed_fields=changed,inert_default=True,
        input_sha256=digest,results=results,
        scope='Frozen recorded inputs and command budgets only; not a closed-loop outcome prediction.'),indent=2))


if __name__=='__main__':main()
