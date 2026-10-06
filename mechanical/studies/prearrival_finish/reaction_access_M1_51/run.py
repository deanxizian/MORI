"""Logged commands for the M1.52 orientation correction and current delivery."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical'
B='/Applications/Blender.app/Contents/MacOS/Blender'
PY='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'
stages={
 'build':'scripts/build.py', 'rebuild':'scripts/check_rebuild.py',
 'validate':'scripts/validate.py', 'export':'scripts/export.py',
 'render':'scripts/render.py', 'electronics':'scripts/export_electronics_detail.py',
 'electronics_check':'scripts/check_electronics_detail.py',
 'engineering':'studies/prearrival_finish/engineering_current.py',
 'structure_metadata':'scripts/finalize_structure_metadata.py',
 'consistency':'scripts/delivery_check.py',
 'body_paths':'studies/prearrival_finish/reaction_access_M1_51/check_body_split.py',
 'access':'studies/prearrival_finish/reaction_access_M1_51/check_access.py',
 'review':'studies/prearrival_finish/reaction_access_M1_51/render_review.py'}
(OUT/'logs').mkdir(exist_ok=True)
for stage in sys.argv[1:]:
 if stage=='animation':cmd=[PY,str(M/'scripts/run_animation.py'),'--defer-publish']
 elif stage=='metal':cmd=[PY,str(M/'scripts/export_wheel_metal.py')]
 elif stage=='catalog':cmd=[B,'--background',str(M/'mori_v1_2.blend'),'-t','6','--python-exit-code','1','--python',str(M/'scripts/catalog.py'),'--','--ids','Yaw_Reaction_Clamp_Nut,Yaw_Reaction_Retainer_Nut']
 else:
  source=M/('mori_electronics_detail.blend' if stage=='electronics_check' else 'mori_v1_2.blend')
  cmd=[B,'--background',str(source),'-t','6','--python-exit-code','1','--python',str(M/stages[stage])]
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 log=OUT/'logs'/(stamp.replace(':','-')+'_'+stage+'.log')
 script=Path(cmd[cmd.index('--python')+1] if '--python' in cmd else cmd[1])
 before=hashlib.sha256(script.read_bytes()).hexdigest()
 print('M1_52_START',stage,flush=True)
 with log.open('w') as f:result=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 row=dict(stage=stage,command=cmd,started_utc=stamp,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          returncode=result.returncode,script_sha256=before,log=str(log.relative_to(ROOT)),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
 record=OUT/'commands.json';history=json.loads(record.read_text()) if record.exists() else []
 history.append(row);record.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
 (OUT/(stage+'.log')).write_text(log.read_text())
 if result.returncode:raise SystemExit(result.returncode)
 if stage=='validate' and json.loads((M/'reports/validation.json').read_text())['counts']['FAIL']:
  raise SystemExit('Current geometry FAIL; inspect report')
 print('M1_52_DONE',stage,flush=True)
