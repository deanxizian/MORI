"""Diagnose concrete ARMED transfer sites and exact retained tracks to reroute.

No reference exception is granted: every reported intersection is outstanding
work, requiring the actual retained track to be rerouted and revalidated.
"""
import ast,json,sys,math
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R145B-via-corridor.json';assert not out.exists()
p=Planner(str(b/'R145B/MORI_Interface_C3.kicad_pcb'),.05,['F.Cu','In3.Cu','B.Cu'],.2);c=p.c;net='/01 {slash} Core/ARMED'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
free,vf,blocked,allowed=p.geometry(net)
body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.F_Cu]);own=unary_union([s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
blocked[0]=unary_union([blocked[0],body.buffer(.102).difference(own.buffer(-.001))])
free[0]=~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)
labs,_=ndimage.label(free[0],np.ones((3,3)));pad=next(q for q in c.pads if c.pad_name(q)=='D1601.2')
seeds=mask(c.shapes[uid(pad),'F.Cu'],p.xx,p.yy)&free[0];labels=[int(x) for x in np.unique(labs[seeds]) if x]
reachable=np.isin(labs,labels)&free[0]
physical=[shape(q,pcb.F_Cu).buffer(.457) for q in c.pads if q.IsOnLayer(pcb.F_Cu)]
# Pads on every layer impose via-pad physical clearance, including unflashed
# through-hole lands. Use the widest native shape, not a visibility test.
physical=[shape(q,c.ids[ly]).buffer(.457) for q in c.pads for ly in LAYERS if q.IsOnLayer(c.ids[ly])]
physical += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
physical += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
physical += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
physical += [s.buffer(.457) for (u,ly),s in c.shapes.items() if c.by_id[u].GetNetname()!=net and not isinstance(c.by_id[u],pcb.PAD)]
raw=~mask(unary_union(physical),p.xx,p.yy)
candidate=raw&reachable&(free[1]|free[2])&p.ground_near
rows=[]
for yi,xi in zip(*np.where(candidate)):
 x,y=float(p.xs[xi]),float(p.ys[yi]);pos=[round(x,4),round(y,4)];void=Point(pos).buffer(.657)
 hits=[]
 for t in c.segments:
  ly=c.board.GetLayerName(t.GetLayer())
  if t.GetNetname()=='GND' or ly not in REFERENCE:continue
  ref=c.shapes[uid(t),ly].intersection(p.ground[REFERENCE[ly]])
  loss=ref.intersection(void).area
  if loss>1e-8:hits.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'reference_loss_area_mm2':loss})
 rows.append({'position_mm':pos,'affected_retained_tracks':hits,'score':20*len(hits)+math.dist(pos,xy(pad.GetPosition()))})
rows.sort(key=lambda r:r['score']);chosen=[]
for r in rows:
 if all(math.dist(r['position_mm'],q['position_mm'])>.25 for q in chosen):chosen.append(r)
 if len(chosen)==12:break
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'source_front_region_cells':int(reachable.sum()),'physical_transfer_candidates':len(rows),'chosen':chosen},indent=2)+'\n')
print(json.dumps({'source_front_region_cells':int(reachable.sum()),'physical_transfer_candidates':len(rows),'chosen':chosen[:5]},indent=2),flush=True)
