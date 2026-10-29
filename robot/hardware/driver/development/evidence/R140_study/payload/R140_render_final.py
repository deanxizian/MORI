"""Render two labelled native-geometry diagnostic views; never save source CAD."""
import json,subprocess,sys,time,hashlib
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');records=[]
for rev,label,bounds,net in [('R140C','CLR-ground',[23,11,32,18],'/CLR_N'),('R140T','power-ground',[10.2,11,18.2,19],'MOTION_3V3')]:
 svg=b/(rev+'-'+label+'-final.svg');png=svg.with_suffix('.png');assert not svg.exists() and not png.exists()
 args=[sys.executable,'robot/hardware/driver/development/scripts/render_inspection.py',str(b/rev/'MORI_Interface_C3.kicad_pcb'),'B.Cu',*[str(x) for x in bounds],str(svg),'--highlight',net]
 t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.time()-t});assert r.returncode==0
 args=['/Users/dean/.local/share/kicad-mcp/venv/bin/python','-c','import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=1200)',str(svg),str(png)]
 t=time.time();r=subprocess.run(args,capture_output=True,text=True);records.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.time()-t});assert r.returncode==0
 records.append({'image':str(png),'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'source_board_sha256':hashlib.sha256((b/rev/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest(),'scope':'Native geometry diagnostic, not a GUI screenshot or full-board qualification'})
f=b/'R140-final-render-commands.json';assert not f.exists();f.write_text(json.dumps(records,indent=2)+'\n')
print('two diagnostic views rendered')
