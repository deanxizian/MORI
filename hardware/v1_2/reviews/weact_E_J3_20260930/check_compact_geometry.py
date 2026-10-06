from update_native_P5R7 import *
import shutil
name,d,p=paths('motion');out=HERE/'reports/motion/compact_geometry';out.mkdir(exist_ok=True)
trial=out/'project';shutil.copytree(d,trial,dirs_exist_ok=True)
(trial/(name+'.kicad_pcb')).write_bytes((HERE/'reports/motion/compact_communications_start.kicad_pcb').read_bytes())
cmd=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(out/'drc.json'),str(trial/(name+'.kicad_pcb'))]
r=subprocess.run(cmd,capture_output=True,text=True);dump(out/'command.json',{'argv':cmd,'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});j=json.loads((out/'drc.json').read_text());print({a:len(j[a])for a in ['violations','unconnected_items','schematic_parity','ignored_checks']});print(json.dumps(j['violations'],indent=2))
