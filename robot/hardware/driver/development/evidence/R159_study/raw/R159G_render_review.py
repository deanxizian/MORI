"""Native polygon views for local review; these are not physical or full-board qualification."""
import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R159G-views';out.mkdir(exist_ok=False);records=[]
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
for revision,board,layers in [('candidate-G',b/'R159G/MORI_Interface_C3.kicad_pcb',['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']),('source',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'),['F.Cu','B.Cu','In2.Cu'])]:
 for layer in layers:
  svg=out/(revision+'-'+layer.replace('.Cu','')+'.svg');png=svg.with_suffix('.png')
  cmd=[py,str(b/'R152_render_highlight.py'),str(board),layer,'36','4','55','18',str(svg),'--highlight','/UPS_BAT']
  r=subprocess.run(cmd,capture_output=True,text=True);records.append({'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  cmd=[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=1520)',str(svg),str(png)]
  r=subprocess.run(cmd,capture_output=True,text=True);records.append({'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  print(str(png),flush=True)
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
