import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad
from interface_completion import axial,replace_owned
load_collections();assembled();bpy.context.view_layer.update();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
name='Head_Pitch_Ear_1_Screw';f=next(r for r in json.loads((HERE/'fastener_current.json').read_text()) if r['id']==name);axis=np.array(f['extracted_axis_outward']);seat=np.array(f['tool_start_mm'])-axis*f['nominal_head_height_mm'];headtop=seat+axis*2
# DIN912 M2 nominal maximum head3.8x2,14mm under-head, no printed change.
bolt=axial(1,14,seat-axis*7,axis)+axial(1.9,2,seat+axis,axis)
static=[]
for n,s in ss.items():
 if n==name:continue
 v=max(0,(bolt^s.m).volume()) if broad(ss[name],s) else 0
 if v>.02:static.append({'part':n,'overlap_mm3':v})
bench={n:s for n,s in ss.items() if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!=name}
r=[]
for leg in [14,16,18,20,25]:
 p=headtop-axis*.7
 # Conservative circular bound for1.5mm AF hex key,0.87mm radius. Bend included.
 tool=axial(.87,leg,p+axis*leg/2,axis)
 tool+=axial(.87,90,p+axis*leg+np.array([0,45,0]),[0,1,0])
 tool+=manifold.Manifold.sphere(.87,32).translate((p+axis*leg).tolist())
 angles=[]
 for angle in range(-180,181,2):
  tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));m=tool.transform(np.array(tr)[:3,:]);hits=[]
  for n,s in bench.items():
   bb=np.array(m.bounding_box())
   if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
   v=max(0,(m^s.m).volume())
   if v>.02:hits.append({'part':n,'volume_mm3':v})
  angles.append({'angle_deg':angle,'hits':hits})
 clear=[a['angle_deg'] for a in angles if not a['hits']];r.append({'short_leg_mm':leg,'clear_angles_deg':clear,'all_samples':angles})
print('PITCH_SOCKET_CANDIDATE',static,[(x['short_leg_mm'],x['clear_angles_deg']) for x in r],flush=True)
(HERE/'pitch_socket_screw_candidate.json').write_text(json.dumps({'main_updated':False,'screw_nominal':'M2x14 DIN912; head3.8x2','printed_geometry_changed':False,'static_hits':static,'tool_trials':r,'tool_selection':'NOT_SELECTED: envelope requirement only, actual L key bend/length and supplier drawing still required'},indent=2))
