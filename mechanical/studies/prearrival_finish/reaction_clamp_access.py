"""Read-only clamp entry/tool study using allowed yaw positions on the bench."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;C=HERE/'thin_candidate_workspace/mechanical'
sys.path.insert(0,str(C/'scripts'))
from common import *
from validate import Solid,rigidtr
from validate_head_retention import hit
from interface_completion import axial
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
bench={n for n,s in ss.items() if s.group=='yaw'} | {'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
rows=[]
for angle in range(-60,61,10):
 tr=np.array(rigidtr(angle,0))[:3,:]
 geom={n:(ss[n].m.transform(tr) if ss[n].group=='yaw' else ss[n].m) for n in bench}
 hits=[]
 for moving,direction in [('Yaw_Reaction_Clamp_Screw',1),('Yaw_Reaction_Clamp_Nut',-1)]:
  for distance in np.arange(0,30.01,.5):
   m=geom[moving].translate((0,direction*float(distance),0))
   for other in bench-{moving}:
    v=hit(m,geom[other])
    if v:hits.append(dict(moving=moving,travel_mm=float(distance),fixed=other,overlap_mm3=v))
 bolt=ss['Yaw_Reaction_Clamp_Screw'];c=(bolt.lo+bolt.hi)/2;p=np.array([c[0],bolt.hi[1]+.05,c[2]])
 tool=axial(1.25,30,p+[0,15,0],[0,1,0]);tool_hits=[]
 for other in bench-{'Yaw_Reaction_Clamp_Screw'}:
  v=hit(tool,geom[other])
  if v:tool_hits.append(dict(fixed=other,overlap_mm3=v))
 rows.append(dict(yaw_deg=angle,status='PASS' if not hits and not tool_hits else 'FAIL',entry_hits=hits,tool_hits=tool_hits))
passed=[r['yaw_deg'] for r in rows if r['status']=='PASS']
out=dict(status='PASS' if passed else 'BLOCKED',source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),main_applied=False,usable_sampled_yaw_deg=passed,rows=rows,
 scope='Yaw subassembly bench, before pitch cradle/head; fixed reaction link, yaw group rotates about existing axis',
 limits=['Final horn/preload still BLOCKED','Straight tool shank is an allocation; final bit/handle not selected','Finite samples only; does not establish reaction-link initial insertion'])
(HERE/'reaction_clamp_access.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('CLAMP_ACCESS',out['status'],passed,flush=True)
