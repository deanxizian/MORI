"""Logged current-main repair/check/export pipeline. No hardware writes."""
import sys,json,subprocess,datetime,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PROJECT=ROOT.parent
BLENDER='/Applications/Blender.app/Contents/MacOS/Blender'
stages=[('build',ROOT/'scripts/build.py',[]),('export',ROOT/'scripts/export.py',[]),
 ('rear_audit',HERE/'audit_rear_repair.py',[]),('validate',ROOT/'scripts/validate.py',[]),
 ('engineering',HERE/'engineering_current.py',[]),
 ('printability',ROOT/'studies/interface_completion/audit_final_prints.py',[]),
 ('body_sequence',ROOT/'scripts/check_head_retention_body_sequence.py',[]),
 ('current_mates',ROOT/'scripts/check_p5r7_current_paths.py',[]),
 ('render',ROOT/'scripts/render.py',[]),('catalog',ROOT/'scripts/catalog.py',['--ids','Head_Rear']),
 ('electronics',ROOT/'scripts/export_electronics_detail.py',[]),
 ('electronics_check',ROOT/'scripts/check_electronics_detail.py',[]),
 ('metal',ROOT/'scripts/export_wheel_metal.py',[]),
 ('structure_metadata',ROOT/'scripts/finalize_structure_metadata.py',[]),
 ('consistency',ROOT/'scripts/delivery_check.py',[])]
parser=argparse.ArgumentParser();parser.add_argument('--from-step',default='build');parser.add_argument('--through',default='consistency');parser.add_argument('--catalog-ids',default='Head_Rear');args=parser.parse_args()
names=[x[0] for x in stages];record=HERE/'geometry_commands.json';history=json.loads(record.read_text()) if record.exists() else []
for name,script,options in stages[names.index(args.from_step):names.index(args.through)+1]:
 if name=='catalog':options=['--ids',args.catalog_ids]
 model=ROOT/('mori_electronics_detail.blend' if name=='electronics_check' else 'mori_v1_2.blend')
 cmd=[BLENDER,'--background',str(model),'--python-exit-code','1','--python',str(script)]+(['--']+options if options else [])
 if name=='metal':cmd=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(script)]
 log=HERE/(name+'_delivery.log');start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('FINISH_GEOMETRY',name,flush=True)
 with log.open('w') as out:result=subprocess.run(cmd,cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT)
 history.append(dict(stage=name,command=cmd,started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=result.returncode,log=str(log.relative_to(PROJECT))))
 record.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
 if result.returncode:raise SystemExit(result.returncode)
 if name=='validate' and json.loads((ROOT/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Unresolved geometry FAIL')
print('GEOMETRY_DELIVERY_FINISHED',flush=True)
