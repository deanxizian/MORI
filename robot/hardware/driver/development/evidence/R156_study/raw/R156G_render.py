import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');o=b/'R156G-views';o.mkdir(exist_ok=False);logs=[]
for tag,board,layers in [('candidate',str(b/'R156G/MORI_Interface_C3.kicad_pcb'),['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']),('source','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',['F.Cu','B.Cu','In2.Cu'])]:
 for ly in layers:
  s=o/(tag+'-'+ly+'.svg');p=o/(tag+'-'+ly+'.png');net='MOTION_3V3' if ly=='In2.Cu' else '/WHEEL_VM'
  for argv in [['robot/.state/c3-completion/venv/bin/python','robot/.state/c3-completion/trials/R152_render_highlight.py',board,ly,'44.5','7','51.5','16.5',str(s),'--highlight',net],['/Users/dean/.local/share/kicad-mcp/venv/bin/python','-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(s),str(p)]]:
   r=subprocess.run(argv,text=True,capture_output=True);logs.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  (o/'commands.json').write_text(json.dumps(logs,indent=2)+'\n');print(tag,ly,flush=True)
