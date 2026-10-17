#!/usr/bin/env python3
"""Finite post-charge comparison after physical supply restoration.

The user restored the lying pose and unplugged the charger. Fresh disabled
preflight is required before launch. This entry preserves trial40 parameters;
charge level is measured, not assumed full. The previous charging entry stays
held. Default invocation has no hardware I/O; no automatic retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_charged_supply import PLAN as HELD_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(HELD_PLAN,
    name='first_layer_post_charge_comparison_v60_1',
    active_message='POST_CHARGE_COMPARISON_ACTIVE: 充电后对照已启动，最多40秒；沿用第40轮参数。净目标0.35Nm、轮速软14/停止15.5rad/s、70°C，向直立软400/停止500°每秒、倒回400、直立后200；异常停止，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial43_overturn: retired post-charge comparison; physical reset and reviewed successor required'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-post-charge-comparison',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
