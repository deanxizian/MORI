"""Review-only: upper ear open nut seat, thicker roof, no thin floor."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,rigidtr
from assembly_issue_fixes import boxm,hex_x,replace
from interface_completion import axial
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
p=P['assembly_issue_fixes']['pitch_nut'];r=next(r for r in json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears'] if r['id']==p['id']);z=r['seat_point_mm'][2];pc=[p['pocket_center_x_mm'],0,z];half=p['pocket_depth_mm']/2
pocket=hex_x(p['pocket_AF_mm'],p['pocket_depth_mm'],pc)+boxm([pc[0]-half,0,z-p['entry_half_height_mm']],[pc[0]+half,8,z+p['entry_half_height_mm']])
height=6.6;pad=boxm([-36,-5.5,z-2.6],[r['seat_point_mm'][0],5.5,z+3.3])
old=ss['Pitch_Yoke'].m
candidate=(old+pad)-pocket-axial(1.1,14,[r['seat_point_mm'][0]-6.99,0,z],[1,0,0])
candidate-=boxm([pc[0]-half,-2.5,z-6],[pc[0]+half,5.501,z-2.099])
add=candidate-old;out={'status':'NOT_TESTED','main_updated':False,'seat_height_before_mm':5.2,'top_extension_mm':.7,'target_roof_mm':1.2,'bottom':'open within nut pocket only; original axial bearing web remains','nut_and_hardware_unchanged':True,'added_mm3':add.volume(),'static_added_collisions':[],'motion_new_collisions':[],'nut_insertion_hits':[]}
for n,s in ss.items():
 if n=='Pitch_Yoke':continue
 v=max(0,(add^s.m).volume())
 if v>.02:out['static_added_collisions'].append({'part':n,'mm3':v,'bounds':list((add^s.m).bounding_box())})
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  m=candidate.transform(np.array(rigidtr(yaw,0))[:3,:]);bb=np.array(m.bounding_box())
  for n,s in ss.items():
   if s.group=='yaw':continue
   fixed=s.m.transform(np.array(rigidtr(yaw,pitch))[:3,:]) if s.group=='pitch' else s.m;cc=np.array(fixed.bounding_box())
   if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
   v=max(0,(m^fixed).volume());prior=max(0,(old.transform(np.array(rigidtr(yaw,0))[:3,:])^fixed).volume())
   if v>max(.02,prior+.02):out['motion_new_collisions'].append({'yaw':yaw,'pitch':pitch,'part':n,'mm3':v})
for d in np.arange(0,12.01,.25):
 v=max(0,(ss[p['id']+'_Nut'].m.translate([0,float(d),0])^candidate).volume())
 if v>.02:out['nut_insertion_hits'].append([float(d),v])
out['poses']=130;out['status']='PASS' if not any(out[k] for k in ['static_added_collisions','motion_new_collisions','nut_insertion_hits']) else 'FAIL'
out['rotation_stops_deg']={}
c=(ss[p['id']+'_Nut'].lo+ss[p['id']+'_Nut'].hi)/2
for sign in [-1,1]:
 out['rotation_stops_deg'][str(sign)]=None
 for angle in range(1,31):
  tr=Matrix.Translation(Vector(c))@Matrix.Rotation(math.radians(sign*angle),4,'X')@Matrix.Translation(-Vector(c))
  if (ss[p['id']+'_Nut'].m.transform(np.array(tr)[:3,:])^candidate).volume()>.02:out['rotation_stops_deg'][str(sign)]=angle;break
out['sections']={}
for label,m in [('current',old),('candidate',candidate)]:
 # x -> slicing Z; output section coordinates are (-Y,Z).
 poly=[[[-y,zz] for y,zz in p] for p in m.rotate([0,90,90]).slice(33.8).to_polygons()]
 sec=manifold.CrossSection([list(reversed(p)) for p in poly])^manifold.CrossSection.square([14,11]).translate([-7,z-5.5])
 out['sections'][label]=[[list(p) for p in poly] for poly in sec.to_polygons()]
(HERE/'pitch_seat_thickness_candidate.json').write_text(json.dumps(out,indent=2))
replace('Pitch_Yoke',candidate);bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'pitch_seat_thickness_candidate.blend'))
print('PITCH_SEAT_THICKNESS',out['status'],out['static_added_collisions'],out['motion_new_collisions'][:5],out['nut_insertion_hits'],flush=True)
