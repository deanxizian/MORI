"""Replay accepted R148E plan after coordinate fix; diagnostic only, not a new adopted board."""
import json,subprocess,sys,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');candidate=b/'R149-compat-R148E';source=Path('robot/.state/c3-completion/baseline_R147L_before_R148E');out=b/'R149-compat-R148E-verify';records=[]
def run(args,expected=(0,)):
    started=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append(dict(argv=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.time()-started));(b/'R149-compat-commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode in expected
run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(b/'R149-compat-drc.json'),str(candidate/'MORI_Interface_C3.kicad_pcb')],(0,5))
run([sys.executable,str(dev/'scripts/verify_trial.py'),str(source),str(candidate),str(out)])
run([sys.executable,str(dev/'scripts/review_planned_delta.py'),str(source/'MORI_Interface_C3.kicad_pcb'),str(candidate/'MORI_Interface_C3.kicad_pcb'),str(dev/'evidence/R148E/plan.json'),str(out/'regression.json'),str(dev/'evidence/R147L/regression.json'),str(b/'R149-compat-planned-delta.json')])
r=json.loads((out/'result.json').read_text());p=json.loads((b/'R149-compat-planned-delta.json').read_text());assert (r['unconnected_items'],r['violations'],r['schematic_parity'],r['erc_violations'])==(26,0,0,0) and p['status']=='PASS'
print(json.dumps(dict(status='PASS',native_result=r,exact_plan_checks=len(p['checks']),adopted=False)))
