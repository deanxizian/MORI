"""Screen INA+ routes against refilled F with outward final pad approach."""
import ast,json,sys,itertools
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168-ina-preflight.json';assert not out.exists()
c=Copper(str(b/'R168F/MORI_Interface_C3.kicad_pcb'));net='Net-(U1702-INA+)';ly='F.Cu'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={f.GetReference():fab(f) for f in c.footprints if f.GetLayer()==pcb.F_Cu}
lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
rows=[]
for x,y in itertools.product([59.4,59.5,59.6],[16,16.1,16.2]):
 pts=[[59.925,12.575],[59.925,13.825],[60.325,14.225],[60.325,14.9],[x,75.225-x],[x,y],[x-(16.3875-y),16.3875],[58.8,16.3875]]
 stroke=LineString(pts).buffer(.1,resolution=64);outside=stroke.difference(lands);hits=[]
 for ref,g in bodies.items():
  area=outside.intersection(g).area
  if area>1e-6:hits.append(dict(kind='body',ref=ref,area_mm2=area))
 for k in c.keepouts:
  if k['tracks'] and ly in k['layers'] and stroke.intersection(k['shape']).area>1e-8:hits.append(dict(kind='guard',name=k['name']))
 for (u,l),s in c.shapes.items():
  if l==ly and c.by_id[u].GetNetname()!=net and stroke.distance(s)<.199999:hits.append(dict(kind='clearance',uuid=u,net=c.by_id[u].GetNetname(),clearance_mm=stroke.distance(s)))
 gap=outside.difference(c.copper['GND','In1.Cu']).area
 if gap>1e-6:hits.append(dict(kind='reference',area_mm2=gap))
 rows.append(dict(x=x,y=y,points_mm=pts,hits=hits))
out.write_text(json.dumps(dict(scope=__doc__,board_sha256=c.sha,U1702_fab_bounds=bodies['U1702'].bounds,rows=rows,adopted=False),indent=2)+'\n')
print('body',bodies['U1702'].bounds)
for r in rows:print(json.dumps(dict(x=r['x'],y=r['y'],hits=r['hits'])))
