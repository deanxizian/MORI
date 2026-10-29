"""Independent final candidate six-layer and focused power-allocation plots."""
import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R153G-views';out.mkdir(exist_ok=False)
records=[]
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
board=str(b/'R153G/MORI_Interface_C3.kicad_pcb')
for layer,bounds,stem,net in [(ly,[0,12,17,27],ly,'/HEAD_6V_RAW') for ly in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']] + [('In2.Cu',[3,15.5,10,24],'RAW_neck','/HEAD_6V_RAW'),('In2.Cu',[3,15.5,10,24],'HEAD_VM_neck','/HEAD_VM')]:
 svg=out/(stem+'.svg');png=out/(stem+'.png')
 for argv in [[py,'robot/hardware/driver/development/scripts/render_inspection.py',board,layer,*map(str,bounds),str(svg),'--highlight',net],['/Users/dean/.local/share/kicad-mcp/venv/bin/python','-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]:
  r=subprocess.run(argv,text=True,capture_output=True)
  records.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  (out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
  assert r.returncode==0
 print(stem,flush=True)
