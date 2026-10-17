"""Pure native-speed target budgeting, with no hardware or scheduling I/O."""
import math
from attitude import Fault,finite,clip
from protocol import RATIO


def velocity_targets(requests,speeds,position_speeds,previous,dt,plan):
    kd_step=RATIO**2/128000000
    kd=math.floor(plan['velocity_native_kd_nm_per_rad_s']/kd_step)*kd_step
    vmax=plan['velocity_target_limit_rad_s']
    slew=plan['velocity_target_slew_rad_s2']
    finite(kd,vmax,slew,dt)
    if not 0<kd<=.15 or not 0<vmax<plan['wheel_speed_limit_rad_s'] or not 0<slew<=200 or not .001<=dt<=plan['loop_gap_s']:
        raise Fault('invalid_native_velocity_plan')
    # The speed packet truncates toward zero; reserve one target LSB in the
    # delayed-feedback predicted torque budget. This is not a hardware clamp.
    speed_lsb=math.tau/(2.56*RATIO)
    cap=plan['predicted_net_torque_limit_nm']-kd*speed_lsb-1e-9
    targets={};limited=False;budget_overrode_slew=False
    for mid in (0,1):
        v,p,request,prior=speeds[mid],position_speeds[mid],requests[mid],previous[mid]
        finite(v,p,request,prior)
        low=max(-vmax,v-cap/kd,p-cap/kd)
        high=min(vmax,v+cap/kd,p+cap/kd)
        if low>high:
            raise Fault('native_velocity_envelope_unavailable')
        desired=clip(v+request/kd,vmax)
        smoothed=prior+clip(desired-prior,slew*dt)
        target=max(low,min(high,smoothed))
        limited|=abs(target-(v+request/kd))>1e-12
        budget_overrode_slew|=abs(target-smoothed)>1e-12
        targets[mid]=target
    return targets,dict(limited=limited,budget_overrode_slew=budget_overrode_slew,
                        quantized_kd=kd,predicted_net_torque_nm={m:kd*(targets[m]-speeds[m]) for m in (0,1)})
