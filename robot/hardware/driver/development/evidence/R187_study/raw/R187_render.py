"""Render all six native copper layers for the local reference repair review."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/.state/c3-completion/trials')
from R152_render_highlight import render
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
out=b/(rev+'-views');out.mkdir(exist_ok=False)
board=b/rev/'MORI_Interface_C3.kicad_pcb'
bounds=[44,5,55,12.5]
for layer in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']:
    net='/01 {slash} Core/WHEEL_TX' if layer=='In2.Cu' else '/01 {slash} Core/IMU_SCL'
    render(board,layer,bounds,out/(layer+'.svg'),net)
with (out/'render_description.json').open('x') as f:
    json.dump(dict(board=str(board),bounds_mm=bounds,layers=6,
                   method='Native padstack copper, actual saved zone fill and keepout polygons; diagnostic top-down projection, not GUI screenshot.',
                   physical='NOT_TESTED'),f,indent=2);f.write('\n')
