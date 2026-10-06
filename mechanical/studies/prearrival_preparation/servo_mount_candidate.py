"""Unapplied alternative: four M2 through-bolts and nuts, no insert hoops in narrow seats."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from purchased_geometry import remove_generated
from render import camera
ROOT=PROJECT
load_collections();material('metal',(.65,.67,.69),.6);assembled();bpy.context.view_layer.update()
o=bpy.data.objects[PREFIX+'Pitch_Yoke'];before=Solid(o).m
mounts=json.loads((ROOT/'mechanical/reports/head_servo_geometry.json').read_text())['mounts'];rows=[];newids=[]
for row in mounts:
 name=row['id'];p=np.array(row['seat_plane_point_mm']);face=np.array(row['ear_top_point_mm']);axis=np.array([0,0,1.]) if row['axis']=='Z' else np.array([1.,0,0])
 # Refill only the old3mm blind pilot before replacing it with a through bore.
 union(o,cyl('restore_old_pilot',row['insert_center_mm'],1.505,3.25,row['axis'],n=64))
 if name=='Head_Yaw_Ear_0':bottom=p-axis*2.6;length=6;recess=1.9
 elif name=='Head_Yaw_Ear_1':bottom=np.array([p[0],p[1],D['head_z']-40]);length=25;recess=0
 else:
  # Existing6mm cheek outer face atX=-42. A2.8mm functional nut recess gives a14mm bolt.
  bottom=np.array([-39.2,p[1],p[2]]);length=14;recess=2.8
 boolean(o,cyl('M2_through',face-axis*(length+5)/2,1.1,length+6,row['axis'],n=64))
 nutcentre=bottom-axis*.8
 if recess:
  # Functional side-open seat, not an exterior ear or long screwdriver groove.
  boolean(o,ring('nut_seat',bottom-axis*(recess+.1)/2,2.55,.05,recess+.2,row['axis'],n=6))
 remove_generated(name+'_Screw');remove_generated(name+'_Insert')
 bolt=cyl(name+'_Screw',face-axis*length/2,1.,length,row['axis'],n=48);union(bolt,cyl('GB823_head',face+axis*.7,1.75,1.4,row['axis'],n=64))
 nut=ring(name+'_Nut',nutcentre,4/math.sqrt(3),1.02,1.6,row['axis'],n=6)
 for q in [bolt,nut]:
  finish(q,'PURCHASED_REFERENCE',name+' 穿栓候选 / 非主模型','metal','yaw',False,note='GB823 nominal M2 screw + GB6170M2 nut reference dimensions; purchase variant/thread qualification pending')
  q['data_status']='ASSUMED';q['model_fidelity']='DRAWING_REFERENCE_ENVELOPE';q['proposal_only']=True;newids.append(q.name.removeprefix(PREFIX))
 rows.append({'id':name,'screw_length_mm':length,'nut_AF_mm':4,'nut_height_mm':1.6,'seat_point_mm':p.tolist(),'nut_bearing_mm':bottom.tolist(),'nut_center_mm':nutcentre.tolist(),'recess_mm':recess,'screw_thread_projection_beyond_nut_mm':float(np.dot(bottom-axis*1.6-(face-axis*length),axis))})
new=Solid(o);partslist=[Solid(q) for q in parts() if q.get('role')=='part' and q.get('group') not in ['dock','coupon']];hits=[]
for n in ['Pitch_Yoke']+newids:
 a=next(s for s in partslist if s.name==n)
 for b in partslist:
  if b.name==n or b.name in newids and n in newids:continue
  if np.any(a.hi<b.lo) or np.any(b.hi<a.lo):continue
  vol=max(0,(a.m^b.m).volume())
  if vol>.02:hits.append({'a':n,'b':b.name,'overlap_mm3':round(vol,4)})
change={'added_mm3':max(0,(new.m-before).volume()),'removed_mm3':max(0,(before-new.m).volume()),'connected_components':len(new.m.decompose())}
report={'status':'FAIL' if hits or change['connected_components']!=1 else 'PASS','candidate_only':True,'applied_to_main':False,'source':'GB823 screw head3.5x1.4; GB6170 nut4AFx1.6; original servo holes retained','mounts':rows,'static_intersections':hits,'solid_change':change,'limits':'Finite static rigid check only; must review assembly access, full motion, print geometry and source fasteners before adoption. No strength PASS.'}
(HERE/'servo_mount_candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'servo_mount_candidate.blend'))
# Two focused workbench views, no geometry mutation for rendering.
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.render.resolution_x=1200;sc.render.resolution_y=800;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
visible={'Pitch_Yoke','Yaw_Servo','Pitch_Servo'}|set(newids)
for q in sc.objects:
 if q.type=='MESH':q.hide_render=q.name.removeprefix(PREFIX) not in visible
for name,loc,target in [('servo_nuts_front',(90,105,170),(0,2,206)),('servo_nuts_back',(-110,-75,250),(0,0,208))]:
 camera(name,loc,target,100);sc.render.filepath=str(HERE/(name+'.png'));bpy.ops.render.render(write_still=True)
print('SERVO_MOUNT_CANDIDATE_COMPLETE',report['status'],hits,flush=True)
