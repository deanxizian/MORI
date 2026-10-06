"""Reproducible M1.35 candidate delivery; no manufacture/strength release."""
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import finalize_head_servo as base
P=base.P;R=base.R
cfg=json.loads((P/'config/geometry.json').read_text());q=cfg['assembly_completion']
ids=','.join(sorted(set(q['changed_existing_ids']+q['new_ids'])))
edge=cfg.get('drive_edge_cleanup',{})
if edge.get('enabled'):ids=','.join(edge['changed_existing_ids'])
groups=[
 [('build',base.blender('build'))],
 [('check_rebuild',base.blender('check_rebuild'))],
 [('validate',base.blender('validate'))],
 [('render',base.blender('render',['--views','all','--size','1000','--samples','20'])),
  ('export',base.blender('export')),('completion_views',base.study('assembly_completion')),
  ('catalog',base.blender('catalog',['--ids',ids]))],
 [('export_electronics_detail',base.blender('export_electronics_detail')),
  ('export_wheel_metal',[base.C,str(R/'scripts/export_wheel_metal.py')]),
  ('structure_metadata',base.blender('finalize_structure_metadata'))],
 [('delivery_check',base.blender('delivery_check')),
  ('electronics_detail_check',base.blender('check_electronics_detail',source=R/'mori_electronics_detail.blend')),
  ('waveshare_bench_check',base.blender('check_waveshare_bench',source=R/'mori_electronics_detail.blend'))],
 [('animation',[sys.executable,str(R/'scripts/run_animation.py'),'--defer-publish'])],
 [('report',[sys.executable,str(R/'scripts/report_completion.py')])]
]
if edge.get('enabled'):
 # Main blend is stable after check_rebuild. Independent renders/exports and
 # the separate animation file can be produced together without resaving it.
 animation_group=next(g for g in groups if g[0][0]=='animation')
 groups.remove(animation_group)
 render_group=next(g for g in groups if g[0][0]=='render')
 render_group.extend(animation_group)
 render_group.extend([('edge_before',base.study('drive_edge_review',P/edge['baseline_blend'],'before')),
                      ('edge_after',base.study('drive_edge_review'))])

def run(item):
 name,cmd=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat();log=R/'reports'/f'completion_final_{name}.log'
 print('COMPLETION',name,'START',flush=True)
 with log.open('w') as out:rc=subprocess.run(cmd,cwd=P,stdout=out,stderr=subprocess.STDOUT).returncode
 print('COMPLETION',name,rc,flush=True)
 return {'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc,'log':str(log.relative_to(R)),'mechanical_revision':cfg['revision']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--from-stage',default='build');args=ap.parse_args()
 first=[g[0][0] for g in groups].index(args.from_stage);path=R/'reports/assembly_completion_commands.json'
 records=json.loads(path.read_text()) if first and path.exists() else []
 keep={n for group in groups[:first] for n,_ in group};records=[r for r in records if r['stage'] in keep]
 for group in groups[first:]:
  with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,group))
  records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
  if any(r['returncode'] for r in rows):raise SystemExit('Failed stage; inspect recorded log')
  if any(r['stage']=='validate' for r in rows) and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Unresolved geometry failure')
  for name,file in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json'),('waveshare_bench_check','waveshare_bench_validation.json')]:
   if any(r['stage']==name for r in rows) and json.loads((R/'reports'/file).read_text())['status']!='PASS':raise SystemExit(name+' failed')
  history_path=R/'reports/commands.json';history=json.loads(history_path.read_text())
  history=[r for r in history if r.get('mechanical_revision')!=cfg['revision']]
  history_path.write_text(json.dumps(history+records,ensure_ascii=False,indent=2)+'\n')
 print('ASSEMBLY_COMPLETION_DELIVERY_COMPLETE',flush=True)
