"""Build, verify, render, export and record the SCS0009/head-seat delivery."""
from pathlib import Path
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
P=Path(__file__).resolve().parents[2];R=P/'mechanical'
B='/Applications/Blender.app/Contents/MacOS/Blender'
C='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'
MASTER=R/'mori_v1_2.blend';records=[]

def blender(script,extra=(),source=MASTER):
    return [B,'--background',str(source),'--python-exit-code','1','--python',str(R/'scripts'/f'{script}.py'),*(['--',*extra] if extra else [])]

def study(name,source=MASTER,tag='after',views=None):
    return [B,'--background',str(source),'--python-exit-code','1','--python',str(R/'studies'/name/'render_review.py'),'--','--tag',tag,*(['--views',views] if views else [])]

def run(item):
    name,command=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    print('SERVO_DELIVERY',name,'START',flush=True);log=R/'reports'/f'servo_final_{name}.log'
    with log.open('w') as f:result=subprocess.run(command,cwd=P,stdout=f,stderr=subprocess.STDOUT)
    print('SERVO_DELIVERY',name,result.returncode,flush=True)
    return {'stage':name,'command':command,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'returncode':result.returncode,'log':str(log.relative_to(R))}

s=json.loads((P/'config/geometry.json').read_text())['head_servo_detail']
catalog=','.join(sorted(set(s['changed_existing_ids']+s['new_ids']+['Pitch_Cradle'])))
groups=[
 [('build',blender('build')),('servo_before',study('head_servo_detail',P/s['baseline_blend'],'before','servo,yoke'))],
 [('check_rebuild',blender('check_rebuild'))],
 [('validate',blender('validate'))],
 [('render',blender('render',['--views','all','--size','1000','--samples','20'])),
  ('export',blender('export')),('export_wheel_metal',[C,str(R/'scripts/export_wheel_metal.py')]),
  ('servo_comparison',study('head_servo_detail')),('animation',[sys.executable,str(R/'scripts/run_animation.py'),'--defer-publish'])],
 [('head_comparison',study('head_cleanup')),('corner_comparison',study('head_corner_chamfer')),
  ('catalog',blender('catalog',['--ids',catalog])),('export_electronics_detail',blender('export_electronics_detail')),
  ('retained_interfaces',[B,'--background',str(MASTER),'--python-exit-code','1','--python',str(R/'studies/drive_cleanup/retained_interfaces.py')]),
  ('drive_comparison',study('drive_cleanup'))],
 [('structure_metadata',blender('finalize_structure_metadata'))],
 [('delivery_check',blender('delivery_check')),('electronics_detail_check',blender('check_electronics_detail',source=R/'mori_electronics_detail.blend'))],
 [('report',[sys.executable,str(R/'scripts/report.py')])]
]

if __name__=='__main__':
    q=argparse.ArgumentParser();q.add_argument('--from-stage',default='build');a=q.parse_args()
    if a.from_stage!='build' and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:
        raise SystemExit('Current geometry has failures; resolve before finalization')
    first=[g[0][0] for g in groups].index(a.from_stage)
    if first:
        old=json.loads((R/'reports/head_servo_commands.json').read_text());keep={n for g in groups[:first] for n,_ in g};records=[r for r in old if r['stage'] in keep]
    for group in groups[first:]:
        with ThreadPoolExecutor(max_workers=len(group)) as pool:new=list(pool.map(run,group))
        records+=new;(R/'reports/head_servo_commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        if any(r['returncode'] for r in new):raise SystemExit('Failed stage; read recorded logs')
        if any(r['stage']=='validate' for r in new) and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:
            raise SystemExit('Geometry failures; not published')
        for name,path in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json')]:
            if any(r['stage']==name for r in new) and json.loads((R/'reports'/path).read_text())['status']!='PASS':raise SystemExit(name+' failed; not published')
    history_path=R/'reports/commands.json';history=json.loads(history_path.read_text()) if history_path.exists() else []
    revision=json.loads((P/'config/geometry.json').read_text())['revision'];history=[r for r in history if r.get('mechanical_revision')!=revision]
    history += [dict(r,mechanical_revision=revision) for r in records];history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    print('SERVO_DELIVERY_COMPLETE',flush=True)
