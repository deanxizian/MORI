import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');o=b/'R154B-views';o.mkdir(exist_ok=False);logs=[]
for tag,board,layers in [('candidate',str(b/'R154B/MORI_Interface_C3.kicad_pcb'),['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']),('source','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',['F.Cu','B.Cu'])]:
 for ly in layers:
  s=o/(tag+'-'+ly+'.svg');p=o/(tag+'-'+ly+'.png')
  for argv in [['robot/.state/c3-completion/venv/bin/python','robot/hardware/driver/development/scripts/render_inspection.py',board,ly,'5.5','21','13','28',str(s),'--highlight','/HEAD_6V_RAW'],['/Users/dean/.local/share/kicad-mcp/venv/bin/python','-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(s),str(p)]]:
   r=subprocess.run(argv,text=True,capture_output=True);logs.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
  (o/'commands.json').write_text(json.dumps(logs,indent=2)+'\n');print(tag,ly,flush=True)
