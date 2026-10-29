"""Independent exact-delta proof of the tested obsolete-via operation.
G and J are NOT accepted boards. Their per-trial edit_plan/edit_manifest records
are preserved separately; only those two auxiliary records are omitted from the
project fixtures, so their intended metadata difference is not a design change.
Every included source member is copied byte-for-byte.
"""
import hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R143J-removal-proof';out.mkdir(exist_ok=False)
proof={}
for rev in ['R143G','R143J']:
 src=b/rev;dest=out/rev
 shutil.copytree(src,dest,ignore=shutil.ignore_patterns('edit_plan.json','edit_manifest.json','*.kicad_prl','*.lck'))
 rows=[]
 for p in dest.rglob('*'):
  if p.is_file():
   rel=p.relative_to(dest);assert p.read_bytes()==(src/rel).read_bytes();rows.append({'path':str(rel),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 proof[rev]=rows
(out/'fixture-members.json').write_text(json.dumps({'scope':__doc__,'members':proof},indent=2)+'\n')
s=Path('robot/hardware/driver/development/scripts');cmds=[]
for args in [[sys.executable,str(s/'audit_candidate.py'),str(out/'R143G/MORI_Interface_C3.kicad_pcb'),str(out/'R143J/MORI_Interface_C3.kicad_pcb'),str(out/'regression.json')],[sys.executable,str(s/'review_planned_delta.py'),str(out/'R143G/MORI_Interface_C3.kicad_pcb'),str(out/'R143J/MORI_Interface_C3.kicad_pcb'),str(b/'R143J-plan.json'),str(out/'regression.json'),str(b/'R143G-audit.json'),str(out/'planned-delta.json')]]:
 t=time.time();r=subprocess.run(args,capture_output=True,text=True);cmds.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.time()-t});(out/'commands.json').write_text(json.dumps(cmds,indent=2)+'\n');assert r.returncode==0
p=json.loads((out/'planned-delta.json').read_text());assert p['status']=='PASS'
print(json.dumps({'status':p['status'],'checks':len(p['checks']),'scope':'obsolete via operation only; G/J engineering failures remain'}))
