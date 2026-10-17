#!/usr/bin/env python3
"""Offline sensor verdict for one finite self-righting log; never opens hardware.

A PASS means the recorded sensor window met the declared criteria. It does not
identify external support, cable contact, slipping tyres, or long-term balance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def assess(report):
    plan=report['plan']
    if plan.get('control_phase') not in ('self_righting','supervised_self_righting'):
        raise ValueError('not_a_self_righting_trial')
    rows=report.get('samples',[])
    enabled=sum(1 for item in report.get('per_id',{}).values()
                for tx in item['transactions'] if (bytes.fromhex(tx['tx_hex'])[2]>>4)&7)
    phases=[]
    stable_since=None
    stable_s=max_stable_s=0.
    first_pitch=None
    best_progress=0.
    last_t=None
    for row in rows:
        a=row['attitude']; state=a.get('self_righting',{})
        phase=state.get('phase')
        if phase and (not phases or phases[-1]!=phase): phases.append(phase)
        if first_pitch is None: first_pitch=a['pitch_deg']
        direction=1. if first_pitch>=0 else -1.
        best_progress=max(best_progress,abs(first_pitch)-direction*a['pitch_deg'])
        wheels=row.get('wheels',{})
        speeds=[]
        for mid in ('0','1'):
            wheel=wheels.get(mid,wheels.get(int(mid),{}))
            feedback=wheel.get('feedback',{})
            if 'speed_rad_s' in feedback:
                speeds.append(report['calibration']['wheel_signs'][mid]*feedback['speed_rad_s'])
        t=a['t']
        contiguous=(last_t is None or 0<t-last_t<=plan['loop_gap_s'])
        stable=(phase=='BALANCE' and len(speeds)==2 and not row.get('control_rejected')
                and abs(a['pitch_deg'])<=plan['stable_pitch_deg']
                and abs(a['pitch_rate_dps'])<=plan['stable_rate_dps']
                and abs(state.get('rolling_velocity_estimate_m_s',math.inf))<=plan['stable_velocity_m_s']
                and abs(speeds[0]-speeds[1])<=plan['stable_differential_speed_rad_s'])
        stable_since=(stable_since if contiguous and stable_since is not None else t) if stable else None
        stable_s=t-stable_since if stable_since is not None else 0.
        max_stable_s=max(max_stable_s,stable_s)
        last_t=t
    # A rejected sensor frame ends the window even if the last valid row looked
    # stable. A runner failure also prevents success, whatever its last phase.
    if report.get('rejected_imu_sample'): stable_s=0.
    passed=(report.get('status')=='PASS' and enabled>0
            and all(p in phases for p in ('RISING','CAPTURE','BALANCE'))
            and stable_s>=plan['stable_duration_s']
            and report.get('elapsed_s',0)>=plan['duration_s']-plan['loop_gap_s']
            and report.get('final_disabled_verified') is True
            and report.get('imu',{}).get('configuration_restored') is True)
    rejected=report.get('rejected_imu_sample')
    rejected_summary=None
    if rejected:
        raw=rejected.get('imu')
        rejected_summary=dict(phase=rejected['phase'],reason=rejected['reason'],
            elapsed_s=rejected.get('elapsed_s'),raw_frame_available=raw is not None,
            accel_norm_g=math.sqrt(sum(v*v for v in raw['accel_g'])) if raw else None)
    rejected_control=next((r for r in reversed(rows) if r.get('control_rejected')),None)
    valid_accels=[r['attitude']['accel_norm_g'] for r in rows]
    return dict(
        evidence='RECORDED_SENSOR_WINDOW',
        sensor_self_righting_status='PASS' if passed else ('FAIL' if enabled else 'NOT_TESTED'),
        trial_status=report.get('status'),reason=report.get('reason'),
        enabled_packets=enabled,active_samples=len(rows),phases=phases,
        elapsed_s=report.get('elapsed_s'),start_pitch_deg=first_pitch,
        last_pitch_deg=rows[-1]['attitude']['pitch_deg'] if rows else None,
        best_recorded_progress_deg=best_progress,
        maximum_stable_window_s=max_stable_s,ending_stable_window_s=stable_s,
        valid_accel_norm_range_g=[min(valid_accels),max(valid_accels)] if valid_accels else None,
        rejected_sensor_sample=rejected_summary,
        rejected_control_sample=dict(
            reason=rejected_control['control_rejected'],
            elapsed_s=rejected_control['elapsed_s'],
            attitude=rejected_control['attitude']) if rejected_control else None,
        final_disabled_verified=report.get('final_disabled_verified'),
        imu_configuration_restored=report.get('imu',{}).get('configuration_restored'),
        onsite_action_judgment_required=False,
        limitations=['External hand/support contact is not measured',
                     'Cable and socket contact are not measured',
                     'Wheel-derived travel is not independently measured ground travel',
                     'A finite sensor window does not establish sustained balance'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    data=args.log.read_bytes()
    result=assess(json.loads(data))
    result.update(source_log=str(args.log),source_log_sha256=hashlib.sha256(data).hexdigest())
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x') as output: output.write(text)
    print(text,end='')


if __name__=='__main__':
    main()
