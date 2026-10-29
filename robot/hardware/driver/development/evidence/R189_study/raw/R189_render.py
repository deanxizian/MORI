"""Render all six native copper layers for the R1304 monitor branch review."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/.state/c3-completion/trials')
from R152_render_highlight import render
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
out=b/(rev+'-views');out.mkdir(exist_ok=False)
board=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb') if rev=='R189-source' else b/rev/'MORI_Interface_C3.kicad_pcb'
bounds=[53,15,65,25]
for layer in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']:
    net='/HEAD_6V_RAW'
    render(board,layer,bounds,out/(layer+'.svg'),net)
with (out/'render_description.json').open('x') as f:
    json.dump(dict(board=str(board),bounds_mm=bounds,layers=6,
                   method='Native padstack copper, actual saved zone fill and keepout polygons; diagnostic top-down projection, not GUI screenshot.',
                   physical='NOT_TESTED'),f,indent=2);f.write('\n')
