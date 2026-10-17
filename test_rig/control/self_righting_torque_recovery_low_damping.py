#!/usr/bin/env python3
"""Finite low native-damping comparison, with body-rate feedback unchanged.

Only the RISING wheel-speed damping is reduced. Native pre-roll damping and
capture/balance damping remain. Feedforward, net-torque, speed, thermal and
sensor limits are unchanged. No default I/O or automatic retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_torque_recovery import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v53_low_native_damping',
    rise_native_wheel_damping_nm_per_rad_s=.001,
    active_message='LOW_DAMPING_RATE_RECOVERY_ACTIVE: 第36轮单次起身开始，最多40秒；减小起身轮速阻尼，保留机身角速度反馈与直立接管阻尼。净目标0.35Nm、15.5rad/s、起身400°/秒、70°C及异常停止线不变，不自动重试。')
PLAN['motion_hold_reason']='trial36_overturn: retired launch; use reviewed successor only'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-low-damping-rate-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
