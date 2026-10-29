"""Read-only all-layer via sites for local supply-bridge repair; never a route acceptance."""
import sys,json
from pathlib import Path
import numpy as np
from shapely import intersects_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R158B/MORI_Interface_C3.kicad_pcb');source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
f=next(f for f in c.footprints if f.GetReference()=='R1701');f.SetPosition(pcb.VECTOR2I(47325000,9700000))
for z in c.zones:
 if z.GetZoneName().startswith('BODY_R1701_'):z.Move(pcb.VECTOR2I(0,-100000))
# These failed new supply tracks will be redesigned. Removing them here is
# solely a search premise, never a source edit or proof of restored power.
exclude={'4150016a-d870-4d6e-beae-177f9b3cdd3a','9fc6be27-25b2-4bce-8f44-98f39ccd1aa1'}
source_ids=set(source.by_id)
exclude|={uid(t) for t in c.segments if uid(t) not in source_ids and t.GetNetname() in ['/UPS_BAT','MOTION_3V3']}
rows=[]
for net,origin,bounds in [('MOTION_3V3',(46.6,10.35),(44.5,8.5,51,11.5)),('/UPS_BAT',(45.35,10.5),(43.8,7.5,47,11.5))]:
 blocks=[g.buffer(.45001) for (u,ly),g in c.shapes.items() if u not in exclude and (isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!=net)]
 blocks += [k['shape'].buffer(.25001) for k in c.keepouts if k['vias']]
 blocks += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v) not in exclude]
 blocked=unary_union(blocks);xs=np.arange(bounds[0],bounds[2]+1e-8,.025);ys=np.arange(bounds[1],bounds[3]+1e-8,.025);xx,yy=np.meshgrid(xs,ys);good=~intersects_xy(blocked,xx,yy)
 sites=[]
 for iy,ix in zip(*np.where(good)):
  x,y=float(xx[iy,ix]),float(yy[iy,ix]);disc=Point(x,y).buffer(.25)
  planes=[ly for ly in ['In2.Cu','In3.Cu'] if any(n==net and l==ly and g.intersects(disc) for n,l,g in source.fills)]
  sites.append({'xy':[round(x,5),round(y,5)],'source_plane_contacts':planes,'move_mm':((x-origin[0])**2+(y-origin[1])**2)**.5})
 sites.sort(key=lambda v:(-len(v['source_plane_contacts']),v['move_mm']));rows.append({'net':net,'sites':sites,'site_count':len(sites)})
 print(json.dumps({'net':net,'count':len(sites),'nearest':sites[:12]}),flush=True)
out=b/'R158-via-sites.json';assert not out.exists();out.write_text(json.dumps({'scope':__doc__,'source_sha256':source.sha,'study_board_sha256':c.sha,'assumed_R1701':[47.325,9.7,180],'excluded_failed_copper':sorted(exclude),'rows':rows,'adopted':False},indent=2)+'\n')
