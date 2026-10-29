"""Native local F/B comparison of an unfinished joint layout; not acceptance."""
import json,subprocess,sys
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');revision=sys.argv[1];out=b/(revision+'-views');out.mkdir(exist_ok=False)
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python';records=[]
for label,board in [(revision,b/revision/'MORI_Interface_C3.kicad_pcb'),('source',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'))]:
 for layer in ['F.Cu','B.Cu']:
  svg=out/(label+'-'+layer.replace('.Cu','')+'.svg');png=svg.with_suffix('.png')
  cmds=[[py,str(b/'R152_render_highlight.py'),str(board),layer,'56','20','70','35',str(svg),'--highlight','Net-(U1301-INB-_{slash}_OV)'],
   [cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=1120)',str(svg),str(png)]]
  for cmd in cmds:
   r=subprocess.run(cmd,text=True,capture_output=True);records.append({'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  print(str(png),flush=True)
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
