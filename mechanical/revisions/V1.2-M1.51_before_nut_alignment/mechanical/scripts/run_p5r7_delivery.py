"""Current-main P5R7 adoption pipeline, with explicit logs and no hardware writes."""
import sys,json,subprocess,datetime,argparse
from pathlib import Path
r=Path(__file__).resolve().parents[1];b='/Applications/Blender.app/Contents/MacOS/Blender'
ap=argparse.ArgumentParser();ap.add_argument('--from-step',default='build');ap.add_argument('--through',default='delivery_check');a=ap.parse_args()
stages=[('build',r/'scripts/build.py',[]),('check_rebuild',r/'scripts/check_rebuild.py',[]),('check_p5r7_adoption',r/'scripts/check_p5r7_adoption.py',[]),('validate',r/'scripts/validate.py',[]),('check_p5r7_current_paths',r/'scripts/check_p5r7_current_paths.py',[]),('body_sequence',r/'scripts/check_head_retention_body_sequence.py',[]),('render',r/'scripts/render.py',[]),('render_p5r7',r/'scripts/render_p5r7_adoption.py',[]),('export',r/'scripts/export.py',[]),('export_wheel_metal',r/'scripts/export_wheel_metal.py',[]),('finalize_structure_metadata',r/'scripts/finalize_structure_metadata.py',[]),('catalog',r/'scripts/catalog.py',['--ids','MCU_Carrier,MCU_Motion,Rear_Interface_PCB,E_Straight_Header,Socket_AC,Socket_BD,Socket_E']),('export_electronics_detail',r/'scripts/export_electronics_detail.py',[]),('check_electronics_detail',r/'scripts/check_electronics_detail.py',[]),('delivery_check',r/'scripts/delivery_check.py',[])]
names=[x[0] for x in stages];first=names.index(a.from_step);last=names.index(a.through);report=r/'reports/p5r7_delivery_commands.json';records=json.loads(report.read_text()) if report.exists() else []
for name,script,args in stages[first:last+1]:
    model=r/('mori_electronics_detail.blend' if name=='check_electronics_detail' else 'mori_v1_2.blend');cmd=[b,'-b',str(model),'--python-exit-code','1','--python',str(script)]+(['--']+args if args else [])
    if name=='export_wheel_metal':cmd=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(script)]
    log=r/'reports'/('p5r7_'+name+'.log');start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('P5R7_DELIVERY',name,flush=True)
    with log.open('w') as f:result=subprocess.run(cmd,cwd=r.parent,stdout=f,stderr=subprocess.STDOUT)
    records.append(dict(stage=name,command=cmd,started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=result.returncode,log=str(log.relative_to(r))));report.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
    if name=='validate' and json.loads((r/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Current geometry validation has FAIL; inspect report before delivery.')
    if name=='check_rebuild' and json.loads((r/'reports/rebuild_check.json').read_text())['status']!='PASS':raise SystemExit('Nondeterministic rebuild')
print('P5R7_DELIVERY_COMPLETE',flush=True)
