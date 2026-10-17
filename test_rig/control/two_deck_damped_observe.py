#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration-only30s observation of the finite trial45 P2.0/D0.075 controller.

The short trial reduced speed/gyro variation compared with trial44 and its
last3s encoder span was about1cm. This does not establish longer convergence
or independence from operator contact. All gains, backend and guards remain;
only observation duration changes. No automatic launch or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_response_damped import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_damped_observe_v118', duration_s=30.,
            control_phase='two_deck_damped_observe',
            active_message='DAMPED_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多30秒。保持上一轮全部控制参数；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-damped-observe',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
