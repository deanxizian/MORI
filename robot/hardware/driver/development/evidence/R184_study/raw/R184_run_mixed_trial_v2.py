"""Build an explicit independent native trial and retain native DRC/regression output."""
import json
import subprocess
import sys
import time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
revision=sys.argv[1]
source=Path(sys.argv[2]) if len(sys.argv)>2 else Path('robot/hardware/driver/development/native')
dest=b/revision
assert not dest.exists()
scripts=Path('robot/hardware/driver/development/scripts')
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
records=[]
def run(step,argv,expected=(0,)):
    t=time.time();r=subprocess.run(argv,text=True,capture_output=True)
    records.append(dict(step=step,argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,elapsed_seconds=time.time()-t))
    (b/(revision+'-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(dict(step=step,returncode=r.returncode,elapsed_seconds=round(time.time()-t,2))),flush=True)
    if r.returncode not in expected:raise SystemExit('Unexpected native command failure; preserved logs')
run('build',[py,str(b/'R184_build_mixed_trial_v2.py'),str(source),str(dest),str(b/(revision+'-plan.json'))])
run('refill_drc',['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(b/(revision+'-drc.json')),str(dest/'MORI_Interface_C3.kicad_pcb')],(0,5))
d=json.loads((b/(revision+'-drc.json')).read_text());print(json.dumps({k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']}),flush=True)
run('audit_from_canonical',[py,str(scripts/'audit_candidate.py'),'robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',str(dest/'MORI_Interface_C3.kicad_pcb'),str(b/(revision+'-audit.json'))])
