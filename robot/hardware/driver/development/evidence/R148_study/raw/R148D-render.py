"""Render each actual native layer in its own process, and convert to reviewable PNGs."""
import json,subprocess,sys,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R148D-views';out.mkdir(exist_ok=False)
records=[]
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
for name,ly,path in [(ly,ly,b/'R148D/MORI_Interface_C3.kicad_pcb') for ly in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']]+[('R147L-B.Cu','B.Cu',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')),('R147L-In3.Cu','In3.Cu',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'))]:
 svg=out/(name+'.svg');png=out/(name+'.png')
 commands=[[py,'robot/hardware/driver/development/scripts/render_inspection.py',str(path),ly,'27','5','49','16',str(svg),'--highlight',('Net-(D1001-K)' if ly=='In3.Cu' else '/16 {slash} Actuator_Direct_Switch/ACT_GATE')],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]
 for args in commands:
  t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':time.time()-t});(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode==0
 print(name,flush=True)
