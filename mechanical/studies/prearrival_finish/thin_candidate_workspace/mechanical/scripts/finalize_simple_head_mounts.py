"""Reproducible M1.34 delivery; preserve the separately disclosed camera hold."""
import sys,json,subprocess,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
import finalize_head_servo as base
from finalize_waveshare import review_gate

P=base.P;R=base.R
before=P/json.loads((P/'config/geometry.json').read_text())['head_mount_simplification']['baseline_blend']
groups=[
 [('build',base.blender('build'))],
 [('check_rebuild',base.blender('check_rebuild'))],
 [('validate',base.blender('validate'))],
 [('render',base.blender('render',['--views','all','--size','1000','--samples','20'])),
  ('export',base.blender('export')),('export_wheel_metal',[base.C,str(R/'scripts/export_wheel_metal.py')]),
  ('simple_before',base.study('simple_head_mounts',before,'before')),
  ('simple_after',base.study('simple_head_mounts'))],
 [('head_comparison',base.study('head_cleanup')),('corner_comparison',base.study('head_corner_chamfer')),
  ('servo_comparison',base.study('head_servo_detail')),('foot_comparison',base.study('head_seat_foot')),
  ('catalog',base.blender('catalog',['--ids','Pitch_Yoke,Pitch_Cradle,Head_Front'])),
  ('export_electronics_detail',base.blender('export_electronics_detail')),
  ('waveshare_comparison',base.blender('waveshare_study_render'))],
 [('structure_metadata',base.blender('finalize_structure_metadata'))],
 [('delivery_check',base.blender('delivery_check')),
  ('electronics_detail_check',base.blender('check_electronics_detail',source=R/'mori_electronics_detail.blend')),
  ('waveshare_bench_check',base.blender('check_waveshare_bench',source=R/'mori_electronics_detail.blend'))],
 [('report',[sys.executable,str(R/'scripts/report.py')])],
 [('delivery_scope',[sys.executable,str(R/'scripts/check_simple_head_delivery.py')])]
]

def run(item):
    name,cmd=item;start=datetime.datetime.now(datetime.timezone.utc).isoformat();log=R/'reports'/f'simple_head_{name}.log'
    print('SIMPLE_HEAD',name,'START',flush=True)
    with log.open('w') as out:rc=subprocess.run(cmd,cwd=P,stdout=out,stderr=subprocess.STDOUT).returncode
    print('SIMPLE_HEAD',name,rc,flush=True)
    return {'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc,'log':str(log.relative_to(R))}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--from-stage',default='build');args=ap.parse_args()
    first=[g[0][0] for g in groups].index(args.from_stage);path=R/'reports/simple_head_mounts_commands.json'
    records=json.loads(path.read_text()) if first and path.exists() else []
    keep={n for group in groups[:first] for n,_ in group};records=[r for r in records if r['stage'] in keep]
    for group in groups[first:]:
        with ThreadPoolExecutor(max_workers=min(4,len(group))) as pool:rows=list(pool.map(run,group))
        records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        if any(r['returncode'] for r in rows):raise SystemExit('Failed stage; inspect recorded log')
        if any(r['stage']=='validate' for r in rows):review_gate()
        for name,file in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json'),('waveshare_bench_check','waveshare_bench_validation.json')]:
            if any(r['stage']==name for r in rows) and json.loads((R/'reports'/file).read_text())['status']!='PASS':raise SystemExit(name+' failed')
    revision=json.loads((P/'config/geometry.json').read_text())['revision'];p=R/'reports/commands.json'
    history=[r for r in json.loads(p.read_text()) if r.get('mechanical_revision')!=revision]
    history += [dict(r,mechanical_revision=revision) for r in records];p.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    print('SIMPLE_HEAD_DELIVERY_COMPLETE',flush=True)
