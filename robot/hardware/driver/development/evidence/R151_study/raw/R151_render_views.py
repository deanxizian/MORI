"""Native diagnostic plots; give highlighted filled zones a distinct color."""
import hashlib,json,subprocess,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R151-source-views';out.mkdir(exist_ok=False)
src=Path('robot/hardware/driver/development/scripts/render_inspection.py')
code=src.read_text();old="'#2b5e50' if net=='GND' else '#456470'";assert code.count(old)==1
renderer=b/'R151_diagnostic_renderer.py';assert not renderer.exists()
renderer.write_text("import sys\nsys.path.insert(0,'robot/hardware/driver/development/scripts')\n"+code.replace(old,"'#38c6ff' if net==highlight else ('#2b5e50' if net=='GND' else '#456470')"))
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());cairo='/Users/dean/.local/share/kicad-mcp/venv/bin/python'
records=[]
jobs=[('D-local-B',b/'R150D/MORI_Interface_C3.kicad_pcb','B.Cu',[29.5,11.0,37,18.5],'Net-(D1001-K)'),('source-HEADVM-In2',Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb'),'In2.Cu',[29.5,13.5,35.5,18.0],'/HEAD_VM'),('C-HEADVM-In2',b/'R150C/MORI_Interface_C3.kicad_pcb','In2.Cu',[29.5,13.5,35.5,18.0],'/HEAD_VM')]
for name,board,ly,bounds,net in jobs:
    svg=out/(name+'.svg');png=out/(name+'.png')
    for args in [[py,str(renderer),str(board),ly,*map(str,bounds),str(svg),'--highlight',net],[cairo,'-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',str(svg),str(png)]]:
        t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append(dict(argv=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.time()-t));(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode==0
(out/'render_metadata.json').write_text(json.dumps(dict(source_renderer_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),modified_renderer_sha256=hashlib.sha256(renderer.read_bytes()).hexdigest(),change='Only the display color of highlighted native filled zones; no geometry mutation or omission',visual_review='NOT_YET_VIEWED'),indent=2)+'\n')
print(out)
