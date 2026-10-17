#!/usr/bin/env python3
"""Read-only finite-trial summary; encoder distance is not floor metrology."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics as st


def rms(values):
    return math.sqrt(st.mean(v * v for v in values))


def summarize(path, windows):
    data = path.read_bytes()
    d = json.loads(data)
    result = dict(log=str(path), sha256=hashlib.sha256(data).hexdigest(),
                  bytes=len(data), status=d['status'], reason=d.get('reason'),
                  elapsed_s=d.get('elapsed_s'), control_cycles=d.get('control_cycles'),
                  final_disabled_verified=d.get('final_disabled_verified'),
                  windows=[])
    for lo, hi in windows:
        samples = [s for s in d.get('samples', []) if lo <= s['elapsed_s'] <= hi]
        if not samples:
            result['windows'].append(dict(window_s=[lo, hi], samples=0))
            continue
        positions = [st.mean(s['rolling_equivalent']['forward_offset_m'].values()) for s in samples]
        speeds = [s['attitude']['velocity_hold']['encoder_velocity_proxy_m_s'] for s in samples]
        pitch = [s['attitude']['pitch_deg'] for s in samples]
        rates = [s['attitude']['pitch_rate_dps'] for s in samples]
        controllers = [s['attitude']['ardupilot_balance'] for s in samples]
        feedback = [w['feedback'] for s in samples for w in s['wheels'].values()]
        row = dict(window_s=[lo, hi], samples=len(samples),
                   pitch_rms_deg=rms(pitch), pitch_mean_deg=st.mean(pitch),
                   pitch_range_deg=[min(pitch), max(pitch)],
                   pitch_rate_rms_dps=rms(rates),
                   encoder_velocity_rms_m_s=rms(speeds),
                   common_encoder_span_m=max(positions)-min(positions),
                   common_encoder_start_end_m=[positions[0], positions[-1]],
                   simultaneous_low_shaft_speed_fraction=st.mean(
                       max(abs(v) for v in c['wheel_rate_forward_rad_s'].values()) < .05
                       for c in controllers),
                   max_shaft_speed_rad_s=max(abs(f['speed_rad_s']) for f in feedback),
                   max_temperature_c=max(f['temperature_c'] for f in feedback),
                   max_feedback_estimated_nm=max(abs(f['torque_estimate_nm']) for f in feedback),
                   max_predicted_net_nm=max(abs(v) for c in controllers for v in c['predicted_net_forward_nm'].values()),
                   adapter_limited_frames=sum(c['adapter_limited'] for c in controllers))
        result['windows'].append(row)
    post = d.get('stop_imu_observation', {})
    rows = post.get('samples', [])
    result['post_stop'] = dict(status=post.get('status'),
                              motor_commands_sent=post.get('motor_commands_sent'),
                              errors=post.get('errors', []),
                              first=rows[0] if rows else None,
                              last=rows[-1] if rows else None)
    result['final_rows'] = d.get('final_rows')
    result['scope'] = ('Finite trial completion and nominal-radius encoder proxies only. '
                       'Same-time windows have different initial conditions; no causal '
                       'or hands-off certification. Post-stop samples are separate.')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', type=Path, nargs='+')
    p.add_argument('--window', nargs=2, type=float, action='append', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if any(not math.isfinite(lo+hi) or not 0 <= lo < hi for lo, hi in a.window):
        p.error('finite increasing nonnegative windows required')
    result = [summarize(path, a.window) for path in a.logs]
    with a.output.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    for d in result:
        print(json.dumps({k: d[k] for k in ('log', 'status', 'reason', 'elapsed_s', 'windows')}))


if __name__ == '__main__':
    main()
