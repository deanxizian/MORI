"""Synchronize the Waveshare reconstruction; preserve explicit known fit failures.

Publication is an engineering-review deliverable, not a manufacturing release.
Any new failure outside the recorded unchanged camera seat stops this pipeline.
"""
from pathlib import Path
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
import finalize_head_servo as base
P=base.P;R=base.R;groups=base.groups
groups[0]=[groups[0][0]]
groups[3]=[(n,cmd) for n,cmd in groups[3] if n!='animation']
groups[3]+=[('waveshare_comparison',base.blender('waveshare_study_render'))]
# Animation generation retains its no-geometry-FAIL gate; no bypass for this review draft.
groups[4]=[(n,base.blender('catalog',['--ids','CAM_Mainboard,Onboard_MIC_L,Onboard_MIC_R,Camera_PCB,Camera_Lens,Display_PCB']) if n=='catalog' else cmd) for n,cmd in groups[4]]
groups[6]+=[('waveshare_bench_check',base.blender('check_waveshare_bench',source=R/'mori_electronics_detail.blend'))]
groups[4]+=[('pad_comparison',base.study('yaw_pad_centering')),('foot_comparison',base.study('head_seat_foot'))]

def run(item):
    name,cmd=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat();log=R/'reports'/f'waveshare_final_{name}.log';print('WAVESHARE',name,'START',flush=True)
    with log.open('w') as out:rc=subprocess.run(cmd,cwd=P,stdout=out,stderr=subprocess.STDOUT).returncode
    print('WAVESHARE',name,rc,flush=True)
    return {'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc,'log':str(log.relative_to(R))}

def review_gate():
    v=json.loads((R/'reports/validation.json').read_text());failed={r['id'] for r in v['checks'] if r['status']=='FAIL'}
    if not failed:return
    q=json.loads((R/'reports/static_interference.json').read_text());pairs={tuple(sorted([r['a'],r['b']])) for r in q['failed_pairs']}
    expected={tuple(sorted(p)) for p in [('Camera_PCB','Display_Frame'),('Camera_Lens','Display_Frame'),('Camera_Lens','Head_Front')]}
    if failed!={'static_rigid_solids','waveshare_nominal_fit'} or pairs!=expected:raise RuntimeError('Unexpected geometry failure; no publication')
    print('WAVESHARE_REVIEW_ONLY: three disclosed camera/old-mount conflicts; printed structure not changed without confirmation.',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--from-stage',default='build');a=ap.parse_args();first=[g[0][0] for g in groups].index(a.from_stage);path=R/'reports/waveshare_commands.json';records=[]
    if first:
        keep={n for g in groups[:first] for n,_ in g};records=[r for r in json.loads(path.read_text()) if r['stage'] in keep]
    for group in groups[first:]:
        with ThreadPoolExecutor(max_workers=len(group)) as pool:rows=list(pool.map(run,group))
        records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        if any(r['returncode'] for r in rows):raise SystemExit('Failed stage; inspect recorded log')
        if any(r['stage']=='validate' for r in rows):review_gate()
        for n,f in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json')]:
            if any(r['stage']==n for r in rows) and json.loads((R/'reports'/f).read_text())['status']!='PASS':raise SystemExit(n+' failed')
    rev=json.loads((P/'config/geometry.json').read_text())['revision'];p=R/'reports/commands.json';history=[r for r in json.loads(p.read_text()) if r.get('mechanical_revision')!=rev];history += [dict(r,mechanical_revision=rev) for r in records];p.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n');print('WAVESHARE_DELIVERY_COMPLETE',flush=True)
