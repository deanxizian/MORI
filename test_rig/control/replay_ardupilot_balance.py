#!/usr/bin/env python3
"""Evaluate new commands on recorded observations; never open any hardware.

Recorded trajectories stay fixed. This is NOT a closed-loop simulation and
cannot predict whether the new controller balances or travels less.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path

from ground_ardupilot_balance import ARDUPILOT_PLAN,ArduPilotBalanceController


def replay(path):
    raw=path.read_bytes();data=json.loads(raw)
    signs={int(k):v for k,v in data['calibration']['wheel_signs'].items()}
    previous={}
    for mid in (0,1):
        arm=[r['feedback'] for r in data['per_id'][str(mid)]['transactions']
             if r['phase']=='arm_zero_confirm' and 'feedback' in r]
        if not arm:raise ValueError('missing_last_pre_active_wheel_feedback')
        previous[mid]=arm[-1]
    controller=ArduPilotBalanceController();frames=[];rejected=None
    for sample in data['samples']:
        attitude={k:v for k,v in sample['attitude'].items() if k not in ('velocity_hold','ardupilot_balance')}
        speeds={m:signs[m]*previous[m]['speed_rad_s'] for m in (0,1)}
        try:
            commands=controller(attitude,speeds)
        except Exception as exc:
            rejected=dict(elapsed_s=sample['elapsed_s'],reason=str(exc));break
        info=attitude['ardupilot_balance']
        frames.append(dict(elapsed_s=sample['elapsed_s'],pitch_deg=attitude['pitch_deg'],
                           rate_dps=attitude['pitch_rate_dps'],**info))
        for mid,row in sample['wheels'].items():previous[int(mid)]=row['feedback']
    old=[r['attitude']['pitch_deg'] for r in data['samples']]
    return dict(source=str(path),sha256=hashlib.sha256(raw).hexdigest(),
                source_stop_reason=data.get('reason'),recorded_elapsed_s=data.get('elapsed_s'),
                recorded_pitch_range_deg=[min(old),max(old)],frames_evaluated=len(frames),
                rejected=rejected,max_abs_ff_nm=max(abs(v) for f in frames for v in f['command_forward_nm'].values()),
                max_abs_i_nm=max(abs(f['i_nm']) for f in frames),
                max_abs_d_nm=max(abs(f['d_nm']) for f in frames),
                adapter_limited_frames=sum(f['adapter_limited'] for f in frames),
                final_i_nm=frames[-1]['i_nm'],frames=frames)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    records=[replay(path) for path in args.logs]
    report=dict(utc=datetime.now(timezone.utc).isoformat(),hardware_opened=False,
                evidence='OFFLINE_FIXED_TRAJECTORY_REPLAY_ONLY',balanced_operation='NOT_TESTED',
                plan=ARDUPILOT_PLAN,records=records)
    with args.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps([{k:v for k,v in r.items() if k!='frames'} for r in records],indent=2))


if __name__=='__main__':main()
