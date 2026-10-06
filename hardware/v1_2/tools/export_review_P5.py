"""Native review-only exports: SVG/PNG, functional schematic PDF, bare STEP."""
import sys,json,hashlib,subprocess
from pathlib import Path
from layout_P5 import paths,H
kind=sys.argv[1];name,d,p,r=paths(kind);cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';out=H/'layout_P5/previews'/name;out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(p);sch=d/(name+'.kicad_sch')
commands=[
 [sys.executable,str(H/'tools/export_track_views_P5.py'),kind],
 [cli,'sch','export','pdf','--output',str(out/(name+'.pdf')),str(sch)],
 [cli,'pcb','export','step','--board-only','--force','--output',str(H/'mechanical'/(name+'_BARE_BOARD.step')),str(p)]]
logs=[]
for i,cmd in enumerate(commands):
 run=subprocess.run(cmd,capture_output=True,text=True);(r/f'review_export_{i}.log').write_text(run.stdout+run.stderr)
 logs.append(dict(argv=cmd,exit_code=run.returncode));assert run.returncode==0,run.stderr
assert sha(p)==before
(r/'review_exports.json').write_text(json.dumps(dict(source_pcb_sha256=before,source_schematic_sha256=sha(sch),bare_STEP_is_populated_assembly=False,manufacturing_outputs=False,commands=logs),indent=2)+'\n')
print(name,'native review images, PDF and bare STEP exported')
