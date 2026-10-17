#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One explicitly requested 60-second repeat of v14, same motion boundaries."""
from air_trial import main as trial_main
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_ardupilot_recovery import RECOVERY_PLAN
from ground_hold_trial import HoldTravel

LONG_PLAN=dict(
    RECOVERY_PLAN,name='restrained_ardupilot_recovery_long_v14b',duration_s=60.,
    active_message='RESTRAINED_GROUND_ACTIVE: 原恢复参数开始，最多 60 秒；现在可轻推一次，随后轻扶防倒并让它自行纠偏。30 度、约 229 度/秒、0.12 Nm、70 度及原转量/故障条件保留；可能提前停止，停止后会撤掉补偿。',
)


def main(argv=None):
    return trial_main(argv,plan=LONG_PLAN,
                      start_flag='--run-restrained-recovery-long',
                      controller=ArduPilotBalanceController(),
                      travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
