"""Record final-model wall/tool audits without changing the assembly."""
import datetime,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
B='/Applications/Blender.app/Contents/MacOS/Blender'
records=[]
for stage,script in [('printability','audit_final_prints.py'),('drivers','check_catalogue_drivers.py')]:
 cmd=[B,'-b',str(R/'mori_v1_2.blend'),'--python-exit-code','1','--python',str(R/'studies/interface_completion'/script)]
 log=R/'reports'/f'six_fixes_{stage}.log';start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=R.parent)
 records.append(dict(stage=stage,command=cmd,started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=r.returncode,log=str(log.relative_to(R))))
 (R/'reports/final_seat_audit_commands.json').write_text(json.dumps(records,indent=2)+'\n')
 if r.returncode:raise SystemExit(r.returncode)
print('FINAL_SEAT_AUDITS_COMPLETE',flush=True)
