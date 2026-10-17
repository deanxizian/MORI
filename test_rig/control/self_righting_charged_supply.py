#!/usr/bin/env python3
"""Held source-only power-condition comparison; no default hardware I/O.

Reuses the best recorded v57 drive/reference settings unchanged. A later test
requires charging to finish, physical charger disconnection, motor power
reconnection and a fresh preflight. Source remains held meanwhile. Full battery
is a controlled variable, not a guarantee of self-righting. No retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_inward_momentum import PLAN as REFERENCE_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(REFERENCE_PLAN,name='first_layer_charged_supply_v60_prepared',
    motion_hold_reason='charging_preparation: require charge complete, physical charger disconnected and motor supply reconnected before a separately reviewed launch',
    active_message='CHARGED_SUPPLY_RECOVERY_ACTIVE: 充足电量对照单次起身，最多40秒；沿用第40轮控制参数。净目标0.35Nm、15.5rad/s、70°C，向直立软400/停止500°每秒、倒回400、直立后200；异常停止，不自动重试。')

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-charged-supply-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
