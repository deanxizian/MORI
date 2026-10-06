"""Read-only production inspection plus an independent local simplification candidate."""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,rigidtr
from monocoque_structure import obj,source_build
from render import camera
from optics_mount import display_transform
here=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
s=P['head_print_cleanup'];q=P['readiness_completion']['lcd'];hz=D['head_z'];old=ss['Display_Frame'].m
rear=q['crossbar_center_y_mm']-q['crossbar_depth_mm']/2+q['crossbar_forward_shift_mm'];front=rear+q['crossbar_depth_mm'];bot=hz+q['original_crossbar_bottom_from_head_mm']-q['lower_crossbar_extension_mm'];top=hz+q['crossbar_top_from_head_mm'];join0,join1=[hz+a for a in s['face_return_z_from_head_mm']]
inner=s['face_return_xy_mm'][0][0];earinner=s['face_return_xy_mm'][1][0];outer=s['face_return_xy_mm'][3][0];oldrear=s['face_return_xy_mm'][0][1]
def block(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def cylinder(point,axis,r,length):
 tr=Matrix.Translation(Vector(point))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
 return manifold.Manifold.cylinder(length,r,r,96).transform(np.array(tr)[:3,:])
m=old
# Only retire the old inner return strips; retain both full-height side ears,
# original nut pockets, mast, camera capture and original tilted LCD seats.
for sign in [-1,1]:
 a,b=sorted([sign*inner,sign*earinner]);m-=block([a,oldrear,join0],[b,rear,join1+.001])
m+=block([-outer,rear,bot],[outer,front,top])
for row in json.loads((ROOT/'reports/readiness_geometry.json').read_text())['LCD']:
 ax=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
 m-=cylinder(p-ax*15,ax,q['clearance_radius_mm'],60)
 m-=cylinder(f-ax*20,ax,q['spotface_radius_mm'],20)
report={'baseline_revision':P['revision'],'status':'CANDIDATE_NOT_APPLIED','proposal':'Remove old rear inner return strips; extend existing front crossbar straight across to retained side ears. Keep4side holes,3LCD posts/counterbores, camera and hardware.','parameters':{'bar_width_before_mm':q['crossbar_width_mm'],'candidate_bar_width_mm':2*outer,'bar_y_mm':[rear,front],'bar_z_mm':[bot,top],'retained_ear_inner_x_mm':earinner,'old_connector_x_abs_mm':[inner,earinner],'old_connector_y_mm':[oldrear,rear]},'volume_before_mm3':old.volume(),'volume_after_mm3':m.volume(),'removed_mm3':max(0,(old-m).volume()),'added_mm3':max(0,(m-old).volume()),'positive_components':sum(x.volume()>.001 for x in m.decompose()),'static_hits':[],'motion_hits':[],'tool_hits':[]}
for n,a in ss.items():
 if n=='Display_Frame':continue
 bb=np.array(m.bounding_box())
 if np.any(bb[3:]<a.lo) or np.any(a.hi<bb[:3]):continue
 v=max(0,(m^a.m).volume())
 if v>.01:report['static_hits'].append({'id':n,'mm3':v})
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  tr=rigidtr(yaw,pitch);moving=m.transform(np.array(tr)[:3,:]);bb=np.array(moving.bounding_box())
  for n,a in ss.items():
   if a.group=='pitch':continue
   aa=a.m.transform(np.array(rigidtr(yaw,0))[:3,:]) if a.group=='yaw' else a.m
   ab=np.array(aa.bounding_box())
   if np.any(bb[3:]<ab[:3]) or np.any(ab[3:]<bb[:3]):continue
   v=max(0,(moving^aa).volume())
   if v>.01:report['motion_hits'].append({'yaw':yaw,'pitch':pitch,'id':n,'mm3':v})
# Preserve four lateral nut paths on detached frame; existing M1.25 checks.
for sign in [-1,1]:
 for rel in s['face_joint_z_from_head_mm']:
  n=f'Face_Joint_{sign}_{rel:.1f}_Nut';a=ss[n]
  for d in np.arange(0,10.01,.5):
   v=max(0,(a.m.translate([-sign*float(d),0,0])^m).volume())
   if v>.01:report['tool_hits'].append({'id':n,'travel_mm':float(d),'mm3':v})
report['poses']=130;report['physical_strength']='NOT_TESTED';report['full_validation']='NOT_RUN; independent local candidate only'
(here/'candidate_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
o=obj('Display_Frame');original_data=o.data;original_material=MATS['frame']
# Use identical material on both comparisons; production is never saved here.
o.data.materials.clear();o.data.materials.append(original_material)
for p in o.data.polygons:p.material_index=0
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True;sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
local={'Display_Frame','Display_PCB','Pitch_Cradle','Pitch_Servo','Yaw_Servo'}|{n for n in ss if n.startswith(('Face_Joint_','LCD_Mount_Screw'))}
manifest={}
for tag,current in [('before',old),('candidate',m)]:
 if tag=='candidate':
  d=current.to_mesh64();inv=o.matrix_world.inverted();me=bpy.data.meshes.new('DisplayFrame_transition_study');me.from_pydata([tuple(inv@Vector(v)) for v in d.vert_properties[:,:3]],[],d.tri_verts.tolist());me.update();o.data=me;me.materials.append(original_material);SOLIDS.pop(o.name,None)
 for name,visible,loc,target,scale in [('detail',local,(-94,122,306),(-32,28,222),49),('part',{'Display_Frame'},(105,-155,312),(0,28,238),91)]:
  for ob in sc.objects:
   if ob.type=='MESH':ob.hide_render=ob.name.removeprefix(PREFIX) not in visible
  camera('frame_'+tag+name,loc,target,scale);sc.render.filepath=str(here/(tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
  manifest[tag+'_'+name]={'camera_mm':loc,'target_mm':target,'scale_mm':scale,'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
(here/'render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Candidate remains a separate study; production blend/config/STLs untouched.
bpy.ops.wm.save_as_mainfile(filepath=str(here/'candidate.blend'))
print('FRAME_TRANSITION_STUDY',json.dumps(report),flush=True)
