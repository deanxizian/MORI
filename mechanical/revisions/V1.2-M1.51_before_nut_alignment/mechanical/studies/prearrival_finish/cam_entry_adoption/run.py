"""Logged M1.50 delivery commands; each stage is independently resumable."""
import datetime,json,subprocess,sys,fcntl,hashlib,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent;P=OUT.parents[3];M=P/'mechanical'
B='/Applications/Blender.app/Contents/MacOS/Blender'
PY='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'
stages={
 'build':('scripts/build.py',[]),
 'rebuild':('scripts/check_rebuild.py',[]),
 'export':('scripts/export.py',[]),
 'rear_audit':('studies/prearrival_finish/audit_rear_repair.py',[]),
 'validate':('scripts/validate.py',[]),
 'focused':('studies/prearrival_finish/cam_entry_adoption/check.py',[]),
 'render':('scripts/render.py',[]),
 'catalog':('scripts/catalog.py',['--ids','CAM_Mainboard']),
 'electronics':('scripts/export_electronics_detail.py',[]),
 'electronics_check':('scripts/check_electronics_detail.py',[]),
 'engineering':('studies/prearrival_finish/engineering_current.py',[]),
 'body_sequence':('scripts/check_head_retention_body_sequence.py',[]),
 'printability':('studies/interface_completion/audit_final_prints.py',[]),
 'structure_metadata':('scripts/finalize_structure_metadata.py',[]),
 'consistency':('scripts/delivery_check.py',[]),
 'detail_render':('studies/prearrival_finish/cam_entry_adoption/render.py',[])}
record=OUT/'commands.json';receipts=OUT/'command_receipts';receipts.mkdir(exist_ok=True)
for name in sys.argv[1:]:
 if name=='animation':cmd=[PY,str(M/'scripts/run_animation.py'),'--defer-publish']
 elif name=='metal':cmd=[PY,str(M/'scripts/export_wheel_metal.py')]
 else:
  script,args=stages[name];blend=M/('mori_electronics_detail.blend' if name=='electronics_check' else 'mori_v1_2.blend')
  cmd=[B,'--background',str(blend),'-t','6','--python-exit-code','1','--python',str(M/script)]+(['--']+args if args else [])
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();print('M1_50',name,flush=True)
 log=OUT/'logs'/(started.replace(':','-')+'_'+name+'.log')
 script=Path(cmd[cmd.index('--python')+1] if '--python' in cmd else cmd[1])
 script_sha=hashlib.sha256(script.read_bytes()).hexdigest()
 with log.open('w') as f:r=subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT)
 shutil.copy2(log,OUT/(name+'.log'))
 row={'script_sha256':script_sha,'script_hash_recorded_at_execution':True,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'stage':name,'command':cmd,'start_utc':started,'finish_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':r.returncode,'log':str(log.relative_to(P))}
 (receipts/(started.replace(':','-')+'_'+name+'.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'commands.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  history=json.loads(record.read_text()) if record.exists() else []
  merged={(x['stage'],x['start_utc']):x for x in history+[json.loads(p.read_text()) for p in receipts.glob('*.json')]}
  record.write_text(json.dumps(sorted(merged.values(),key=lambda x:x['start_utc']),ensure_ascii=False,indent=2)+'\n')
 if r.returncode:raise SystemExit(r.returncode)
 if name=='validate' and json.loads((M/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Geometry checks failed; inspect report.')
 print('M1_50_DONE',name,flush=True)
