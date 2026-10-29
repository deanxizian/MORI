"""Render native source layers independently; no PCB mutation."""
import json, subprocess, time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R149-source-views';out.mkdir(exist_ok=False)
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
records=[]
for name,ly,bounds in [('F.Cu','F.Cu',[25,3,62,30]),('B.Cu','B.Cu',[25,3,62,30]),('In3.Cu','In3.Cu',[25,3,62,30]),('MUX-B.Cu','B.Cu',[27,3.5,35,8.5])]:
    svg=out/(name+'.svg');png=out/(name+'.png')
    for args in [[py,'robot/hardware/driver/development/scripts/render_inspection.py','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',ly,*map(str,bounds),str(svg),'--highlight','/ACT_CURRENT_FILTERED'],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]:
        start=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append(dict(argv=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.time()-start));(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode==0
