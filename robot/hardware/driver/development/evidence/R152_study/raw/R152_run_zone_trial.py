"""Execute a named independent trial with preserved command evidence."""
import json,subprocess,sys,time
from pathlib import Path
base=Path('robot/.state/c3-completion/trials')
revision,source=sys.argv[1:3]
dest=base/revision;assert not dest.exists()
script=Path('robot/hardware/driver/development/scripts')
records=[]
def run(tag,args,expected=(0,)):
 t=time.time();r=subprocess.run(args,capture_output=True,text=True)
 records.append({'step':tag,'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.time()-t})
 (base/(revision+'-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps({'step':tag,'returncode':r.returncode,'elapsed_seconds':round(time.time()-t,2)}),flush=True)
 if r.returncode not in expected:raise SystemExit('Unexpected failure; preserved output in commands record')
run('build',[sys.executable,str(base/'R152_build_zone_trial.py'),str(base/source),str(dest),str(base/(revision+'-plan.json'))])
run('refill_drc',['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(base/(revision+'-drc.json')),str(dest/'MORI_Interface_C3.kicad_pcb')],(0,5))
d=json.loads((base/(revision+'-drc.json')).read_text())
print(json.dumps({k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']}),flush=True)
run('audit_from_canonical',[sys.executable,str(script/'audit_candidate.py'),'robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',str(dest/'MORI_Interface_C3.kicad_pcb'),str(base/(revision+'-audit.json'))],(0,1,2))
