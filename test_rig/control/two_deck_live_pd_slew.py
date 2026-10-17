#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite supervised AP P/D slew-modifier comparison; no default hardware I/O.

Keep stationary-integral v150, rotor speed input and all original guards.
Use ending trial83 D0.070. SMAX2Nm/s is an experimental command threshold,
not a measured actuator capability. Local modifier floor0.5 is explicit.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from stationary_integral import StationaryIntegralLiveController
from two_deck_live_stationary_integral import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-pd-slew'
PLAN=dict(BASE,name='two_deck_live_pd_slew_v151',ap_kd=.070/BASE['output_scale_nm'],
          allow_pd_slew_modifier=True,ap_smax=2./BASE['output_scale_nm'],
          ap_slew_tau_s=1.,ap_slew_min_modifier=.5,
          active_message='PD_SLEW_ACTIVE: 补偿已开始，红点亮、提示音一次。使用ArduPilot原有快振检测调节P/D，保留至少一半名义增益；P3.25/I0.60/D0.070，其他控制和保护保留。最多5分钟、0.12Nm、6rad/s、正负30度、80度及原转量/异常条件，到时红点灭、两声后接住。')


class PDSlewLiveController(StationaryIntegralLiveController):
    def extra_telemetry(self,sample):
        a=sample['attitude'];z=a['ardupilot_balance'];out=super().extra_telemetry(sample)
        mod=z['pd_slew_modifier'];g=a['live_tuning']['current']
        out.update(pd_slew_modifier=mod,pd_slew_raw_modifier=z['pd_slew_raw_modifier'],
                   pd_output_slew_nm_s=z['pd_slew_rate_output_per_s']*PLAN['output_scale_nm'],
                   effective_pitch_p=g['pitch_p']*mod,effective_pitch_d=g['pitch_d']*mod)
        return out


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=VelocityDiagnosticsController(),
                          travel_factory=HoldTravel,description=__doc__)
    channel=TuningChannel(gains(PLAN))
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=PDSlewLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
