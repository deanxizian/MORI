"""Render each actual native layer in its own process, and convert to reviewable PNGs."""
import json,subprocess,sys,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R147L-views';out.mkdir(exist_ok=False)
records=[]
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
for name,ly,path in [(ly,ly,b/'R147L/MORI_Interface_C3.kicad_pcb') for ly in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']]+[('R145I-B.Cu','B.Cu',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'))]:
 svg=out/(name+'.svg');png=out/(name+'.png')
 commands=[[py,'robot/hardware/driver/development/scripts/render_inspection.py',str(path),ly,'32','7','51','23',str(svg),'--highlight','/16 {slash} Actuator_Direct_Switch/ACT_GATE'],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]
 for args in commands:
  t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':time.time()-t});(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode==0
 print(name,flush=True)
