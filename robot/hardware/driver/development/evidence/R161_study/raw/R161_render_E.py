"""Actual six-layer local inspection images for the incomplete R161E board."""
import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161E-views';out.mkdir(exist_ok=False)
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python';records=[]
board=b/'R161E/MORI_Interface_C3.kicad_pcb'
jobs=[('right-'+ly,ly,48,12,70,35,1320) for ly in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']]
jobs += [('bias-B','B.Cu',39,20,46,30,840),('source-right-B','B.Cu',48,12,70,35,1320)]
for label,layer,x0,y0,x1,y1,width in jobs:
 src=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb') if label.startswith('source-') else board
 svg=out/(label+'.svg');png=svg.with_suffix('.png')
 cmds=[[py,str(b/'R152_render_highlight.py'),str(src),layer,str(x0),str(y0),str(x1),str(y1),str(svg),'--highlight','Net-(U1301-INB-_{slash}_OV)'],
  [cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=int(sys.argv[3]))',str(svg),str(png),str(width)]]
 for cmd in cmds:
  r=subprocess.run(cmd,text=True,capture_output=True);records.append({'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 print(str(png),flush=True)
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
