"""Locate physically legal supply vias that would require explicit old-trace rerouting.

Does not waive reference loss: every reported intersection is a required repair.
No native board is saved; candidate acceptance still uses the unchanged audit.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R155-supply-via-diagnostic.json';assert not out.exists()
p=Planner(b/'R155A/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);c=p.c;net='MOTION_3V3'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
gs=p.routing_groups(net);g=next(g for g in gs if g['pads']==['C1303.1','U1301.5'])
free,vf,obs,allowed=p.geometry(net);bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu]);lands=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
ob=obs[0].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
fb=~mask(ob,p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)
lab,n=ndimage.label(fb,np.ones((3,3)));target=mask(g['layers']['B.Cu'],p.xx,p.yy)&fb
labels=set(int(x) for x in lab[target]);labels.discard(0);reachable=np.isin(lab,list(labels))
via_ob=[s.buffer(.457) for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!=net]
via_ob += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
via_ob += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
via_ob += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
physical=~mask(unary_union(via_ob),p.xx,p.yy)
window=mask(box(39,20,46,27),p.xx,p.yy,True);eligible=physical&reachable&window
rows=[]
for yi,xi in zip(*np.where(eligible)):
 pos=(float(p.xs[xi]),float(p.ys[yi]));hole=Point(pos).buffer(.655)
 hits=[]
 for t in c.segments:
  ly=c.board.GetLayerName(t.GetLayer())
  if t.GetNetname()=='GND' or ly not in REFERENCE:continue
  hit=c.shapes[uid(t),ly].intersection(p.ground[REFERENCE[ly]]).intersection(hole)
  if hit.area>1e-6:hits.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'area_mm2':hit.area,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'width_mm':t.GetWidth()/1e6})
 rows.append({'position_mm':[round(x,6) for x in pos],'strict_reference_free':bool(vf[yi,xi]),'old_reference_repairs_required':hits,'score':len(hits)*10+math.dist(pos,(42.9,24.275))})
rows.sort(key=lambda r:r['score'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'target_region_cells':int(reachable.sum()),'eligible_cells':len(rows),'proposals':rows,'adopted':False},indent=2)+'\n')
print(json.dumps({'eligible_cells':len(rows),'top':rows[:12]}))
