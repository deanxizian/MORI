"""Plot actual OV-trial CAM power fill and retained reference; no board mutation."""
import json,subprocess,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R151-OV-views';out.mkdir(exist_ok=False)
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python';records=[]
for name,board in [('source',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')),('A',b/'R151A/MORI_Interface_C3.kicad_pcb')]:
    svg=out/(name+'.svg');png=out/(name+'.png')
    for args in [[py,str(b/'R151_diagnostic_renderer.py'),str(board),'In3.Cu','55','23','66','31',str(svg),'--highlight','/07 {slash} CAM_Protection_Start/CAM_BAT_OUT'],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]:
        t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append(dict(argv=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.time()-t));(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode==0
print(out)
