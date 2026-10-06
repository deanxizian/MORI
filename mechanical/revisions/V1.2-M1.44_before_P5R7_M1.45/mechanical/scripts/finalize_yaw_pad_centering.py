"""Rebuild, check and synchronize the confirmed M1.32 local pad contour change."""
from pathlib import Path
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
import finalize_head_servo as base

P=base.P;R=base.R;groups=base.groups
groups[0]=[groups[0][0]]
groups[3]+=[('pad_comparison',base.study('yaw_pad_centering')),('foot_comparison',base.study('head_seat_foot'))]
groups[4]=[(n,base.blender('catalog',['--ids','Pitch_Yoke']) if n=='catalog' else cmd) for n,cmd in groups[4]]

def run(item):
    name,command=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    print('PAD_DELIVERY',name,'START',flush=True);log=R/'reports'/f'pad_final_{name}.log'
    with log.open('w') as out:rc=subprocess.run(command,cwd=P,stdout=out,stderr=subprocess.STDOUT).returncode
    print('PAD_DELIVERY',name,rc,flush=True)
    return {'stage':name,'command':command,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'returncode':rc,'log':str(log.relative_to(R))}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--from-stage',default='build');a=parser.parse_args()
    first=[g[0][0] for g in groups].index(a.from_stage);path=R/'reports/yaw_pad_centering_commands.json'
    records=[]
    if first:
        keep={n for g in groups[:first] for n,_ in g};records=[r for r in json.loads(path.read_text()) if r['stage'] in keep]
    for group in groups[first:]:
        with ThreadPoolExecutor(max_workers=len(group)) as pool:rows=list(pool.map(run,group))
        records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        if any(r['returncode'] for r in rows):raise SystemExit('Failed stage; inspect recorded log')
        if any(r['stage']=='validate' for r in rows) and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:
            raise SystemExit('Geometry failure; no publishing')
        for name,file in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json')]:
            if any(r['stage']==name for r in rows) and json.loads((R/'reports'/file).read_text())['status']!='PASS':raise SystemExit(name+' failed')
    rev=json.loads((P/'config/geometry.json').read_text())['revision'];p=R/'reports/commands.json'
    history=[r for r in json.loads(p.read_text()) if r.get('mechanical_revision')!=rev]
    history += [dict(r,mechanical_revision=rev) for r in records];p.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    print('PAD_DELIVERY_COMPLETE',flush=True)
