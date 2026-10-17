"""Frozen input-only estimate comparison. Never opens devices or predicts balance."""
import csv,hashlib,json,math,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from causal_rotor_pitch_velocity import CausalRotorPitchVelocity


def main():
    p=Path('logs/two-deck-balance-87-quiet-baseline.json');digest=hashlib.sha256()
    with p.open('rb') as f:
        for q in iter(lambda:f.read(4*1024*1024),b''):digest.update(q)
    assert digest.hexdigest()=='3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285'
    raw=json.loads(p.read_text());est=CausalRotorPitchVelocity();out=[];warmup=0
    path=Path('logs/trial87-velocity-inputs-causal.csv')
    with path.open('x',newline='') as f:
        writer=csv.writer(f);writer.writerow(['elapsed_s','imu_t','pitch_deg','gyro_dps','left_position_forward_rad',
            'right_position_forward_rad','left_host_receive_t','right_host_receive_t',
            'left_reported_forward_rad_s','right_reported_forward_rad_s','old_control_m_s','new_causal_m_s'])
        for s in raw['samples']:
            if 'cycle_work_ms' not in s:continue
            a=s['attitude'];pos={int(k):v for k,v in a['wheel_position_forward_rad'].items()}
            times={int(k):v for k,v in a['wheel_feedback_received_monotonic'].items()}
            speeds={int(k):v for k,v in a['ardupilot_balance']['wheel_rate_forward_rad_s'].items()}
            result=est.update(a['t'],a['pitch_deg'],pos,times,speeds)
            old=a['velocity_frame_control']['selected_control_proxy_m_s'];new=result['corrected_proxy_m_s']
            writer.writerow([s['elapsed_s'],a['t'],a['pitch_deg'],a['pitch_rate_dps'],
                pos[0],pos[1],times[0],times[1],speeds[0],speeds[1],old,new])
            if result['ready']:out.append((s['elapsed_s'],old,new))
            else:warmup+=1
    result=dict(status='PASS',scope=__doc__,raw_sha256=digest.hexdigest(),window_s=est.window,
        complete_ready_frames=len(out),warmup_frames=warmup,estimator_rejections=0,
        csv=str(path),windows=[])
    for lo,hi in [(10,40),(120,150),(220,250),(350,380),(450,480)]:
        ss=[x for x in out if lo<=x[0]<=hi]
        rms=lambda seq:math.sqrt(statistics.mean(v*v for v in seq))
        result['windows'].append(dict(interval_s=[lo,hi],samples=len(ss),
            old_control_rms_m_s=rms(x[1] for x in ss),new_causal_rms_m_s=rms(x[2] for x in ss),
            difference_rms_m_s=rms(x[2]-x[1] for x in ss),
            mean_old_m_s=statistics.mean(x[1] for x in ss),mean_new_m_s=statistics.mean(x[2] for x in ss)))
    result['limitations']='Only frozen-input estimator behavior. Causal20ms secant changes bandwidth/delay. No measured ground truth, friction/latency identification or closed-loop stability/recovery proof. Not connected to live trial90.'
    with Path('logs/trial87-causal-velocity-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
