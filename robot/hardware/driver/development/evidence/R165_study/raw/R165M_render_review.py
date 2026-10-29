"""Native geometry review images for R165M and the unchanged R159H source.
These are diagnostic drawings, not GUI screenshots or physical qualification.
"""
import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R165M-views';out.mkdir(exist_ok=False);records=[]
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
requests=[]
for name,board,layers in [('candidate',b/'R165M/MORI_Interface_C3.kicad_pcb',['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']),('source',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'),['F.Cu','B.Cu','In3.Cu'])]:
 for layer in layers:requests.append((name+'-'+layer.replace('.Cu',''),board,layer,[40,14,70,35],'/13 {slash} Head_Fault_Delay/HEAD_UV_N',2400))
for layer in ['B.Cu','In3.Cu','In4.Cu']:
 requests.append(('transfer-'+layer.replace('.Cu',''),b/'R165M/MORI_Interface_C3.kicad_pcb',layer,[52.3,29,57.2,34.6],'/FAULT_N',1100))
for name,board,layer,bounds,highlight,width in requests:
 svg=out/(name+'.svg');png=svg.with_suffix('.png')
 commands=[[py,str(b/'R152_render_highlight.py'),str(board),layer,*map(str,bounds),str(svg),'--highlight',highlight], [cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=int(sys.argv[3]))',str(svg),str(png),str(width)]]
 for argv in commands:
  r=subprocess.run(argv,capture_output=True,text=True);records.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 print(str(png),flush=True)
(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
