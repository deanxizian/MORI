import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
p=Planner('robot/.state/c3-completion/trials/R137G/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','In2.Cu','F.Cu'],.5);c=p.c
n='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT';free,vf,obs,allowed=p.geometry(n)
def fab(f):
 ly=pcb.F_Fab if f.GetLayer()==pcb.F_Cu else pcb.B_Fab;ls=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=ly:continue
  a,b=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:ls.append(LineString([a,b]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(ls))))
fs={f.GetReference():f for f in c.footprints};fb={r:fab(f) for r,f in fs.items()}
win=(p.xx>18)&(p.xx<23)&(p.yy>15)&(p.yy<18)
vm=win&vf&free[1]&free[3]&p.ground_near
coords=[p.point((0,int(y),int(x))) for y,x in zip(*np.where(vm))];coords=sorted(coords,key=lambda a:Point(a).distance(Point(19.9,16)))
rows=[]
for pt in coords[:60]:
 ps=Point(pt).buffer(.252)
 rows.append({'point':pt,'front_bodies':[r for r,f in fs.items() if f.GetLayer()==pcb.F_Cu and fb[r].intersects(ps)]})
d={'source_sha256':c.sha,'valid_native_site_count':len(coords),'sites':rows,'bounds':{r:fb[r].bounds for r in ['L701','L901','Q1401','R1406','R1407']}}
Path('robot/.state/c3-completion/trials/R137G-cam-local-sites.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
