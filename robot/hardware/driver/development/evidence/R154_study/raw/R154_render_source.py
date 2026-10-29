import json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');o=b/'R154-source-views';o.mkdir(exist_ok=False);logs=[]
for ly in ['F.Cu','B.Cu','In2.Cu','In3.Cu']:
 s=o/(ly+'.svg');p=o/(ly+'.png')
 for argv in [['robot/.state/c3-completion/venv/bin/python','robot/hardware/driver/development/scripts/render_inspection.py','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',ly,'30','18','49','35',str(s),'--highlight','Net-(U1301-INB-_{slash}_OV)'],['/Users/dean/.local/share/kicad-mcp/venv/bin/python','-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(s),str(p)]]:
  r=subprocess.run(argv,text=True,capture_output=True);logs.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 (o/'commands.json').write_text(json.dumps(logs,indent=2)+'\n');print(ly,flush=True)
