"""Local non-ground via locations screened against actual R159A geometry.
Native refill, routing, old supplies and reference checks remain required.
"""
import sys,json
from pathlib import Path
import numpy as np
from shapely import intersects_xy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R159A/MORI_Interface_C3.kicad_pcb');rows=[]
for net,id_,origin,bounds in [('MOTION_3V3','9fc6be27-25b2-4bce-8f44-98f39ccd1aa1',(50.9,6.5),(48.5,5.8,53,8.0)),('/01 {slash} Core/MOTION_5V','c9ef7bb5-bef9-48b7-b4cf-23501fe0a859',(44.56,10.1),(44.4,9.9,44.9,10.2))]:
 exclude={id_}
 blocks=[g.buffer(.45001) for (u,ly),g in c.shapes.items() if u not in exclude and (isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!=net)]
 blocks += [k['shape'].buffer(.25001) for k in c.keepouts if k['vias']]
 blocks += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v) not in exclude]
 blocked=unary_union(blocks);xs=np.arange(bounds[0],bounds[2]+1e-8,.025);ys=np.arange(bounds[1],bounds[3]+1e-8,.025);xx,yy=np.meshgrid(xs,ys);good=~intersects_xy(blocked,xx,yy)
 sites=[]
 for iy,ix in zip(*np.where(good)):
  x,y=float(xx[iy,ix]),float(yy[iy,ix]);disc=Point(x,y).buffer(.25)
  planes=[ly for ly in ['In2.Cu','In3.Cu'] if any(n==net and l==ly and g.intersects(disc) for n,l,g in c.fills)]
  sites.append({'xy':[round(x,5),round(y,5)],'prior_fill_contacts':planes,'move_mm':((x-origin[0])**2+(y-origin[1])**2)**.5})
 sites.sort(key=lambda v:v['move_mm']);rows.append({'net':net,'sites':sites,'site_count':len(sites)})
 print(json.dumps({'net':net,'count':len(sites),'nearest':sites[:12]}),flush=True)
out=b/'R159-via-sites.json';assert not out.exists();out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'rows':rows,'adopted':False},indent=2)+'\n')
