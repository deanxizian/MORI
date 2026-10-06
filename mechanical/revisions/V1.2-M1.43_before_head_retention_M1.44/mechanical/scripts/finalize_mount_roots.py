"""Update actual geometry, previews, exports and editable/video assembly deliverables."""
from pathlib import Path
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
import finalize_head_servo as base
P,R=base.P,base.R
cfg=json.loads((P/'config/geometry.json').read_text())
ids=','.join(cfg['mount_root_cleanup']['changed_existing_ids'])
groups=[
 [('build',base.blender('build'))],
 [('check_rebuild',base.blender('check_rebuild'))],
 [('validate',base.blender('validate'))],
 [('render',base.blender('render',['--views','all','--size','1000','--samples','20'])),
  ('export',base.blender('export')),
  ('readiness_views',base.study('readiness_completion')),
  ('completion_views',base.study('assembly_completion')),
  ('animation',[sys.executable,str(R/'scripts/run_animation.py'),'--defer-publish'])],
 [('mount_audit',[base.B,'--background',str(base.MASTER),'--python-exit-code','1','--python',str(R/'studies/mount_root_cleanup/audit_mounts.py')]),
  ('mount_views',[base.B,'--background',str(base.MASTER),'--python-exit-code','1','--python',str(R/'studies/mount_root_cleanup/render_current.py')]),
  ('catalog',base.blender('catalog',['--ids',ids])),
  ('export_electronics_detail',base.blender('export_electronics_detail')),
  ('export_wheel_metal',[base.C,str(R/'scripts/export_wheel_metal.py')]),
  ('structure_metadata',base.blender('finalize_structure_metadata'))],
 [('delivery_check',base.blender('delivery_check')),
  ('electronics_detail_check',base.blender('check_electronics_detail',source=R/'mori_electronics_detail.blend'))],
 [('report',[sys.executable,str(R/'scripts/report_completion.py')])]]

def run(item):
 name,cmd=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 log=R/'reports'/f'mount_roots_final_{name}.log';print('mount_roots',name,'START',flush=True)
 with log.open('w') as f:rc=subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT).returncode
 print('mount_roots',name,rc,flush=True)
 return {'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc,'log':str(log.relative_to(R)),'mechanical_revision':cfg['revision']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--from-stage',default='build');args=ap.parse_args()
 first=[g[0][0] for g in groups].index(args.from_stage);path=R/'reports/mount_roots_commands.json'
 records=json.loads(path.read_text()) if first and path.exists() else []
 keep={n for group in groups[:first] for n,_ in group};records=[r for r in records if r['stage'] in keep]
 for group in groups[first:]:
  with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,group))
  records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
  history_path=R/'reports/commands.json';history=json.loads(history_path.read_text())
  history=[r for r in history if r.get('mechanical_revision')!=cfg['revision']]
  history_path.write_text(json.dumps(history+records,ensure_ascii=False,indent=2)+'\n')
  if any(r['returncode'] for r in rows):raise SystemExit('Failed stage; inspect its recorded log')
  if any(r['stage']=='validate' for r in rows) and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Geometry failures')
  for name,file in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json')]:
   if any(r['stage']==name for r in rows) and json.loads((R/'reports'/file).read_text())['status']!='PASS':raise SystemExit(name+' failed')
 print('MOUNT_ROOTS_DELIVERY_COMPLETE',flush=True)
