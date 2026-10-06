"""Look for a bench entry sequence using rigid transforms only, no CAD edits."""
from pathlib import Path
import sys,json,hashlib,itertools
HERE=Path(__file__).resolve().parent
baseline='--baseline' in sys.argv
C=HERE.parents[1] if baseline else HERE/'thin_candidate_workspace/mechanical'
sys.path.insert(0,str(C/'scripts'))
from common import *
from validate import Solid
from validate_head_retention import hit
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
movers=['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn']
combined=manifold.Manifold()
for n in movers:combined+=ss[n].m
fixture=ss['Pitch_Yoke'].m
def transform(axis,angle,pivot_z,lift=0):
 r=Matrix.Translation((0,0,pivot_z))@Matrix.Rotation(math.radians(angle),4,axis)@Matrix.Translation((0,0,-pivot_z))
 d=r.to_3x3()@Vector((0,0,lift))
 return Matrix.Translation(d)@r
trials=[];found=None
for axis,pz,angle in itertools.product(['X','Y'],[160,165,170,175,155,180],[4,6,8,10,12,16,20,24,30,-4,-6,-8,-10,-12,-16,-20,-24,-30]):
 path=[];first=None
 for a in np.linspace(0,angle,int(abs(angle)*2)+1):
  tr=transform(axis,float(a),pz);v=hit(combined.transform(np.array(tr)[:3,:]),fixture)
  if v:first=dict(phase='tilt',angle_deg=float(a),lift_mm=0,overlap_mm3=v);break
  path.append(dict(phase='tilt',angle_deg=float(a),lift_mm=0,matrix=np.array(tr).tolist()))
 if first is None:
  for d in np.arange(.5,90.01,.5):
   tr=transform(axis,angle,pz,float(d));v=hit(combined.transform(np.array(tr)[:3,:]),fixture)
   if v:first=dict(phase='lift',angle_deg=angle,lift_mm=float(d),overlap_mm3=v);break
   path.append(dict(phase='lift',angle_deg=angle,lift_mm=float(d),matrix=np.array(tr).tolist()))
 trials.append(dict(axis=axis,pivot_z_mm=pz,angle_deg=angle,clear_samples=len(path),first_collision=first))
 if first is None:
  found=dict(axis=axis,pivot_z_mm=pz,angle_deg=angle,lift_mm=90,path=path);break
out=dict(status='PASS' if found else 'BLOCKED',scope='Rigid bench sequence candidate only; final horn installation/preload remains BLOCKED',
 source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 main_applied=False,moving=movers,fixture=['Pitch_Yoke'],
 absent_by_sequence='Yaw/Pitch servos, their ear fasteners, bearings, body bridge and head are not installed at this bench stage',
 proposal=found,trials=trials,
 limits=['No source geometry or hardware changed','No proof of continuous sweep, print deformation, hand access or final horn assembly','Retained current unselected horn and trial fastener envelopes'])
(HERE/('reaction_link_entry_baseline.json' if baseline else 'reaction_link_entry.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('REACTION_ENTRY',out['status'],'trials',len(trials),None if not found else {k:v for k,v in found.items() if k!='path'},flush=True)
