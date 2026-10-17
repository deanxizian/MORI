#!/usr/bin/env python3
"""One finite synchronized pre-roll comparison; no default I/O or auto rearm.

Returns to400deg/s inward reference. Both wheels must reach12.5rad/s reverse
feedback before reversal, or the unchanged0.4s preparation deadline. Existing
14rad/s speed governor applies. Extra PRE_ROLL stop15rad/s remains below the
unchanged15.5rad/s total stop. Torque/thermal/travel guards are unchanged.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_inward_momentum import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v59_1_synced_preroll',
    abort_lift_direction_speed_only=True,
    pre_roll_target_rad_s=12.5,pre_roll_speed_limit_rad_s=15.,pre_roll_target_both_wheels=True,
    active_message='SYNCED_PREROLL_RECOVERY_ACTIVE: 第42轮单次起身开始，最多40秒；双轮反向预滚目标12.5rad/s再换向，准备段15rad/s停止，总轮速15.5、净目标0.35Nm、70°C不变。向直立软400/停止500°每秒，倒回400，直立后200；不自动重试。')
PLAN['motion_hold_reason']='trial42_overturn: retired launch; power-condition audit pending'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-synced-preroll-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
