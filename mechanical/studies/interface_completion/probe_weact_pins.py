import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from native_electronics import board_transform
c=json.loads((PROJECT/P['detail_fit']['weact_mesh']).read_text());rows=[]
mp=P['layout_cleanup']['motion_carrier'];r=np.array([[0,-1,0],[-1,0,0],[0,0,-1.]])
t=np.array([*mp['center_xy_mm'],mp['pcb_reference_z_mm']])+[61.016,116.078,1.595+mp['core_socket_height_assumed_mm']]
for i in [32,159,160,161,162]:
 s=c['solids'][i];m=manifold.Manifold(manifold.Mesh64(np.array(s['vertices_mm']),np.array(s['triangles'],dtype=np.uint64)))
 pts=[]
 for sec in m.slice(-1).decompose():
  poly=np.concatenate(sec.to_polygons());cent=(poly.min(0)+poly.max(0))/2;p=r@np.array([*cent,0])+t;pts.append(p[:2].tolist())
 rows.append({'solid':i,'pin_xy':pts})
inv=json.loads((ROOT/'sources/populated_P5/inventory.json').read_text())['boards']['motion'];fp=next(f for f in inv['footprints'] if f['reference']=='U100');rt,tt=board_transform('motion')
pads=[{'id':p['number'],'xy':(rt@np.array([p['xy_mm'][0],-p['xy_mm'][1],0])+tt)[:2].tolist()} for p in fp['pads']]
print(json.dumps({'source_pins':rows,'native_pads':pads},indent=2));(HERE/'weact_pin_alignment.json').write_text(json.dumps({'source_pins':rows,'native_pads':pads},indent=2))
