"""Render an incomplete native trial for real local six-layer inspection."""
import json,subprocess,sys
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-views');out.mkdir(exist_ok=False)
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python';records=[]
board=b/rev/'MORI_Interface_C3.kicad_pcb'
jobs=[('right-'+ly,ly,60,23,70,35,1000) for ly in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']]
jobs += [('bias-B','B.Cu',39,20,46,30,840)]
if len(sys.argv)>2 and sys.argv[2]=='--upper':
 jobs += [('upper-'+ly,ly,56,14,65,25.5,900) for ly in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']]
for label,layer,x0,y0,x1,y1,width in jobs:
 svg=out/(label+'.svg');png=svg.with_suffix('.png')
 cmds=[[py,str(b/'R152_render_highlight.py'),str(board),layer,str(x0),str(y0),str(x1),str(y1),str(svg),'--highlight','Net-(U1301-INA+_{slash}_UV)'],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=int(sys.argv[3]))',str(svg),str(png),str(width)]]
 for cmd in cmds:
  r=subprocess.run(cmd,text=True,capture_output=True);records.append({'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 print(str(png),flush=True)
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
