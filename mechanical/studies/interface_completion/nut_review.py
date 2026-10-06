"""Nominal catalogue hex-nut review, no main model/PCB mutation."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad
load_collections();assembled();bpy.context.view_layer.update()
f={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())};ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};rows=[]
for name,nut in ss.items():
 if 'Nut' not in name:continue
 screw=name.replace('Nut','Screw');axis=np.array(f[screw]['extracted_axis_outward']);mid=(nut.lo+nut.hi)/2
 oldheight=float((nut.v@axis).max()-(nut.v@axis).min());m3=name.startswith(('Yaw_Base','Wheel_Cap_Clamp'));af,height=(5.5,2.4) if m3 else (4,1.6)
 host='Drive_Bridge' if name.startswith(('Drive_','Wheel_Cap')) else 'Display_Frame' if name.startswith('Face_') else 'Pitch_Yoke' if name.startswith('Head_') else 'Yaw_Base' if name.startswith('Yaw_Base') else 'Yaw_Reaction_Link'
 # Closed nut envelope, centered from the existing seat-facing plane.
 newmid=mid+axis*(oldheight-height)/2;tr=Matrix.Translation(Vector(newmid))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
 mm=(manifold.Manifold.cylinder(height,af/math.sqrt(3),af/math.sqrt(3),6,center=True)-manifold.Manifold.cylinder(height+.1,1.5 if m3 else 1,1.5 if m3 else 1,64,center=True)).transform(np.array(tr)[:3,:])
 # Preserve current hex clocking for comparison (the original ring construction
 # rotates around Y for X-axis features, Z/Y tracking can differ by30 degrees).
 best=None
 for phi in range(0,60):
  rot=Matrix.Translation(Vector(newmid))@Matrix.Rotation(math.radians(phi),4,Vector(axis))@Matrix.Translation(-Vector(newmid));shape=mm.transform(np.array(rot)[:3,:]);vol=max(0,(shape^ss[host].m).volume())
  if best is None or vol<best[0]:best=(vol,phi,shape)
 neutral,clocking,shape=best;contacts=[]
 for angle in range(0,61):
  rot=Matrix.Translation(Vector(newmid))@Matrix.Rotation(math.radians(angle),4,Vector(axis))@Matrix.Translation(-Vector(newmid));v=max(0,(shape.transform(np.array(rot)[:3,:])^ss[host].m).volume())
  if v>.02:contacts.append(angle)
 sh=f[screw];face=np.array(sh['tool_start_mm'])-axis*sh['nominal_head_height_mm'];tip=face-axis*sh['nominal_shank_length_mm'];rear=newmid-axis*height/2;projection=float((rear-tip)@axis)
 rows.append({'id':name,'screw':screw,'host':host,'reference_standard':'GB/T6170/ISO4032 dimensional reference','thread':'M3' if m3 else 'M2','AF_mm':af,'height_mm':height,'current_model_height_mm':oldheight,'nominal_candidate_center_mm':newmid.tolist(),'neutral_collision_mm3':neutral,'hex_clocking_deg':clocking,'first_positive_rotation_contact_deg':min(contacts) if contacts else None,'positive_thread_projection_mm':projection,'retention':'NO_ROTATION_CAPTURE: counterhold tool or pocket correction required' if not contacts else 'Nominal positive rotation stop present','status':'FAIL' if neutral>.02 or projection<0 else 'BLOCKED' if not contacts else 'PASS'})
(HERE/'nut_review.json').write_text(json.dumps({'rows':rows,'main_updated':False,'limits':'No strength, thread helix, torque or purchase qualification. A hex nut that rotates freely cannot be labelled captive; neutral fit alone is insufficient.'},indent=2))
print('NUT_REVIEW',[(r['id'],r['status'],r['first_positive_rotation_contact_deg'],r['positive_thread_projection_mm']) for r in rows],flush=True)
