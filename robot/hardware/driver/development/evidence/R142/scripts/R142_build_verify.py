"""Fresh reconstruction and independent acceptance checks; no adoption here."""
import json,subprocess,sys,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');scripts=Path('robot/hardware/driver/development/scripts');source=Path('robot/hardware/driver/development/native');dest=b/'R142';output=b/'R142-verification'
assert not dest.exists() and not output.exists() and (b/'R142-plan.json').exists()
records=[]
def run(step,args,expected=(0,)):
 t=time.time();r=subprocess.run(args,capture_output=True,text=True)
 records.append({'step':step,'argv':args,'returncode':r.returncode,'elapsed_seconds':time.time()-t,'stdout':r.stdout,'stderr':r.stderr})
 (b/'R142-build-verification-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps({'step':step,'returncode':r.returncode,'elapsed_seconds':round(time.time()-t,2)}),flush=True)
 if r.returncode not in expected:raise SystemExit('Failure preserved in R142 command record')
run('build_from_R134N',[sys.executable,str(scripts/'build_trial.py'),str(source),str(dest),str(b/'R142-plan.json')])
run('refill_save_drc',['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(b/'R142-refill-drc.json'),str(dest/'MORI_Interface_C3.kicad_pcb')],(0,5))
run('native_erc_drc_regression',[sys.executable,str(scripts/'verify_trial.py'),str(source),str(dest),str(output)])
run('planned_delta',[sys.executable,str(scripts/'review_planned_delta.py'),str(source/'MORI_Interface_C3.kicad_pcb'),str(dest/'MORI_Interface_C3.kicad_pcb'),str(b/'R142-plan.json'),str(output/'regression.json'),'robot/hardware/driver/development/evidence/R134N/regression.json',str(output/'planned-delta.json')])
run('mounted_body_review',[sys.executable,str(b/'R141_body_review.py'),str(source/'MORI_Interface_C3.kicad_pcb'),str(dest/'MORI_Interface_C3.kicad_pcb'),str(output/'body-review.json')])
r=json.loads((output/'result.json').read_text());d=json.loads((output/'planned-delta.json').read_text());body=json.loads((output/'body-review.json').read_text())
print(json.dumps({'native':r,'planned_delta':d['status'],'planned_errors':d['errors'],'planned_check_count':len(d['checks']),'same_face_body_projections':body['same_face_projections']},indent=2),flush=True)
