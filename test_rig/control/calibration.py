#!/usr/bin/env python3
"""Offline, user-labelled gravity-pose calibration. Never opens hardware.

The upright reference is a geometric pose, not a measured balance/COM zero.
Forward is the direction labelled by the onsite operator, not a CAD guess.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def norm(a):
    return math.sqrt(dot(a,a))


def unit(a):
    n = norm(a)
    if not math.isfinite(n) or n < 1e-9:
        raise ValueError('degenerate_vector')
    return [v/n for v in a]


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def pose(rows, duration=2.0):
    """Select a full quiet interval after initial settling; fail on motion.

    These are engineering acceptance thresholds for this calibration, not a
    vendor accuracy specification. They do not prove the operator pose label.
    """
    candidates=[]
    for start in range(0,len(rows),10):
        first=rows[start]['elapsed_s']
        if first < .5:
            continue
        window=[]
        for row in rows[start:]:
            if row['elapsed_s']-first > duration+.02:
                break
            window.append(row)
        if len(window)<duration*80 or window[-1]['elapsed_s']-first<duration-.02:
            continue
        if any(b['elapsed_s']-a['elapsed_s']>.03 for a,b in zip(window,window[1:])):
            continue
        result={}
        for k in ('accel_g','gyro_dps'):
            result[k+'_mean']=[statistics.mean(r['imu'][k][i] for r in window) for i in range(3)]
            result[k+'_std']=[statistics.pstdev(r['imu'][k][i] for r in window) for i in range(3)]
        if not all(math.isfinite(v) for values in result.values() for v in values):
            continue
        if not .95 <= norm(result['accel_g_mean']) <= 1.05:
            continue
        if max(result['accel_g_std'])>.01 or max(result['gyro_dps_std'])>.5:
            continue
        if norm(result['gyro_dps_mean'])>1:
            continue
        if max(norm(r['imu']['gyro_dps']) for r in window)>3:
            continue
        score=norm(result['accel_g_std'])+norm(result['gyro_dps_std'])/100
        result.update(start_s=first,end_s=window[-1]['elapsed_s'],samples=len(window),quiet_score=score)
        candidates.append(result)
    if not candidates:
        raise ValueError('no_stationary_two_second_interval')
    return min(candidates,key=lambda r:r['quiet_score'])


def basis(upright, forward):
    up=unit(upright['accel_g_mean'])
    fwd=unit(forward['accel_g_mean'])
    angle=math.degrees(math.acos(max(-1,min(1,dot(up,fwd)))))
    if not 7<=angle<=45:
        raise ValueError('forward_pose_must_differ_by_7_to_45_deg')
    gravity_direction=unit([fwd[i]-dot(up,fwd)*up[i] for i in range(3)])
    # In sensor/body coordinates dg/dt = -omega x g. Thus for a positive
    # pitch causing gravity to move towards gravity_direction, omega=d x up.
    pitch_axis=unit(cross(gravity_direction,up))
    return dict(up_axis_raw=up,forward_gravity_axis_raw=gravity_direction,
                positive_pitch_gyro_axis_raw=pitch_axis,
                gyro_bias_dps=upright['gyro_dps_mean'],forward_pose_deg=angle,
                gyro_sign_dynamic_check='NOT_TESTED',wheel_signs='NOT_TESTED',
                balanced_operation='NOT_TESTED',
                zero_meaning='user-held geometric upright; not center-of-mass equilibrium')


def angles(imu,cal):
    a=imu['accel_g']; g=imu['gyro_dps']
    return dict(pitch_accel_deg=math.degrees(math.atan2(dot(a,cal['forward_gravity_axis_raw']),dot(a,cal['up_axis_raw']))),
                pitch_rate_dps=dot([g[i]-cal['gyro_bias_dps'][i] for i in range(3)],cal['positive_pitch_gyro_axis_raw']))


def read_pose(path):
    data=path.read_bytes(); report=json.loads(data)
    if report['status']!='PASS' or not report['final_disabled_verified'] or not report['imu']['configuration_restored']:
        raise ValueError('capture_did_not_finish_cleanly')
    for item in report['per_id'].values():
        for tx in item['transactions']:
            packet=bytes.fromhex(tx['tx_hex'])
            if packet[2]&0x70 or any(packet[3:16]):
                raise ValueError('capture_contains_nonzero_motor_command')
    return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),**pose(report['samples']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upright',type=Path,required=True)
    parser.add_argument('--forward',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    upright,forward=read_pose(args.upright),read_pose(args.forward)
    report=dict(status='PASS',evidence='BENCH_POSES',upright=upright,forward=forward,**basis(upright,forward))
    with args.output.open('x') as f:
        json.dump(report,f,indent=2); f.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
