"""Offline descriptive balancing command analysis; never opens devices.

Closed-loop terms and correlations cannot identify actuator accuracy,
friction, backlash or cause. Distance remains a nominal encoder proxy.
"""
import hashlib,json,math,statistics
from pathlib import Path


def main():
    p=Path('logs/two-deck-balance-87-quiet-baseline.json');digest=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):digest.update(b)
    assert digest.hexdigest()=='3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285'
    r=json.loads(p.read_text());rows=[s for s in r['samples'] if 'cycle_work_ms' in s]
    result={k:r.get(k) for k in ('status','reason','elapsed_s','control_cycles','final_disabled_verified')}
    result.update(sha256=digest.hexdigest(),bytes=p.stat().st_size,
        imu_restored=r['imu']['configuration_restored'],cam=r.get('cam_indicator',{}),
        controller_summary=r['controller_summary'],windows=[])
    for lo,hi in [(10,40),(120,150),(220,250),(350,380),(450,480)]:
        ss=[s for s in rows if lo<=s['elapsed_s']<=hi];aa=[s['attitude']['ardupilot_balance'] for s in ss]
        z=dict(interval=[lo,hi],samples=len(ss),terms_nm={k:dict(mean=statistics.mean(x[k] for x in aa),
            rms=math.sqrt(statistics.mean(x[k]**2 for x in aa)))
            for k in ('p_nm','i_nm','d_nm','requested_net_nm')},per_wheel={})
        x=[(s['elapsed_s'],s['attitude']['pitch_deg']) for s in ss[::4]]
        mean=statistics.mean(y for _,y in x);t0=x[0][0];spectrum=[]
        for j in range(2,151):
            hz=j/10
            c=sum((y-mean)*math.cos(math.tau*hz*(t-t0)) for t,y in x)
            q=sum((y-mean)*math.sin(math.tau*hz*(t-t0)) for t,y in x)
            spectrum.append((c*c+q*q,hz))
        z['dominant_pitch_frequencies_hz']=[hz for _,hz in sorted(spectrum,reverse=True)[:4]]
        for mid in ('0','1'):
            speed=[abs(s['wheels'][mid]['feedback']['speed_rad_s']) for s in ss]
            ff=[s['wheels'][mid]['command_forward_nm'] for s in ss]
            net=[s['attitude']['ardupilot_balance']['predicted_net_forward_nm'][mid] for s in ss]
            events=[];start=None;commands=[]
            for i,(s,v) in enumerate(zip(ss,speed)):
                if v<=.0171:
                    if start is None:start=s['elapsed_s'];commands=[]
                    commands.append(net[i])
                else:
                    if start is not None and s['elapsed_s']-start>=.04:
                        post=[speed[k] for k in range(i,min(i+21,len(speed))) if ss[k]['elapsed_s']-s['elapsed_s']<=.1]
                        events.append(dict(time=s['elapsed_s'],low_s=s['elapsed_s']-start,
                            net_mean=statistics.mean(commands),net_min=min(commands),net_max=max(commands),next100ms_peak=max(post)))
                    start=None;commands=[]
            z['per_wheel'][mid]=dict(zero_fraction=statistics.mean(v==0 for v in speed),
                low_fraction=statistics.mean(v<=.0171 for v in speed),
                speed_rms=math.sqrt(statistics.mean(v*v for v in speed)),
                ff_rms=math.sqrt(statistics.mean(v*v for v in ff)),
                net_rms=math.sqrt(statistics.mean(v*v for v in net)),
                low_to_motion_events=len(events),events_first=events[:8],
                median_low_s=statistics.median(e['low_s'] for e in events) if events else None,
                median_peak=statistics.median(e['next100ms_peak'] for e in events) if events else None)
        result['windows'].append(z)
    result['sample_attitude_schema']=rows[len(rows)//2]['attitude']
    result['scope']=__doc__
    out=Path('logs/trial87-command-response-review.json')
    with out.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cam','controller_summary','sample_attitude_schema')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
