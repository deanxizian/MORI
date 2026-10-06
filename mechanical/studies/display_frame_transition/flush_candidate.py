"""Independent second candidate: co-planar ear/front beam, level bottom.

Production sources/Blend/STLs remain unchanged. All dimensions derive from
the current shared configuration; this is a review candidate, not a release.
"""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,rigidtr
from monocoque_structure import obj,source_build
from render import camera
here=Path(__file__).parent
source_files=['config/geometry.json','contracts/mechanical_interfaces.json','contracts/components.json','mechanical/mori_v1_2.blend']
hashes={f:hashlib.sha256((PROJECT/f).read_bytes()).hexdigest() for f in source_files}
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
s=P['head_print_cleanup'];q=P['readiness_completion']['lcd'];hz=D['head_z'];old=ss['Display_Frame'].m
rear=q['crossbar_center_y_mm']-q['crossbar_depth_mm']/2+q['crossbar_forward_shift_mm']
front=rear+q['crossbar_depth_mm'];bot=hz+q['original_crossbar_bottom_from_head_mm']-q['lower_crossbar_extension_mm']
top=hz+q['crossbar_top_from_head_mm'];join0,join1=[hz+a for a in s['face_return_z_from_head_mm']]
inner=s['face_return_xy_mm'][0][0];earinner=s['face_return_xy_mm'][1][0]
outer=s['face_return_xy_mm'][3][0];oldrear=s['face_return_xy_mm'][0][1];earback=s['face_return_xy_mm'][2][1]
lcd=json.loads((ROOT/'reports/readiness_geometry.json').read_text())['LCD']
def block(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def cylinder(point,axis,r,length):
 tr=Matrix.Translation(Vector(point))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
 return manifold.Manifold.cylinder(length,r,r,96).transform(np.array(tr)[:3,:])
def open_lcd(m):
 for row in lcd:
  ax=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
  m-=cylinder(p-ax*15,ax,q['clearance_radius_mm'],60)
  m-=cylinder(f-ax*20,ax,q['spotface_radius_mm'],20)
 return m
previous=old
for sign in [-1,1]:
 a,b=sorted([sign*inner,sign*earinner]);previous-=block([a,oldrear,join0],[b,rear,join1+.001])
previous=open_lcd(previous+block([-outer,rear,bot],[outer,front,top]))
m=previous
# M1.38 used top-.001 for its replacement cutter. Volume probes confirm a
# 0.000992 mm old-bar film behind the new beam, outside the central mast.
# Remove that numerical remnant, retaining the real mast and optical seats.
for sign in [-1,1]:
 a,b=sorted([sign*s['face_mast_width_mm']/2,sign*earinner])
 m-=block([a,oldrear,top-.01],[b,rear,top+.01])
for sign in [-1,1]:
 a,b=sorted([sign*earinner,sign*outer])
 # Bring only the existing ears' front faces to the beam's front plane.
 m+=block([a,rear,top],[b,front,join1])
 # Bring their bottom faces to the beam's continuous bottom plane.
 m+=block([a,earback,bot],[b,rear,join0])
m=open_lcd(m)
report={'baseline_revision':P['revision'],'status':'CANDIDATE_NOT_APPLIED','proposal':'Both existing ears and beam share one front plane and one level bottom; remove old inner return strips. Preserve side bores/nut pockets, optical mounting datums and all hardware.',
 'parameters':{'bar_width_mm':2*outer,'common_front_y_mm':front,'common_bottom_z_mm':bot,'ear_x_abs_mm':[earinner,outer],'ear_y_mm':[earback,front],'ear_z_mm':[bot,join1], 'retired_front_step_mm':front-rear,'retired_bottom_step_mm':join0-bot,'retired_legacy_film_nominal_mm':.001},
 'volume_original_mm3':old.volume(),'volume_previous_candidate_mm3':previous.volume(),'volume_candidate_mm3':m.volume(),
 'removed_from_production_mm3':max(0,(old-m).volume()),'added_to_production_mm3':max(0,(m-old).volume()),
 'positive_components':sum(x.volume()>.001 for x in m.decompose()),'static_hits':[],'motion_hits':[],'side_nut_insertion_hits':[],'LCD_checks':[],
 'source_hashes':hashes,'tool_version':bpy.app.version_string,'physical_strength':'NOT_TESTED','full_validation':'NOT_RUN; independent local candidate only'}
def collisions(shape,objects):
 hits=[];bb=np.array(shape.bounding_box())
 for n,a in objects.items():
  ab=np.array(a.bounding_box())
  if np.any(bb[3:]<ab[:3]) or np.any(ab[3:]<bb[:3]):continue
  v=max(0,(shape^a).volume())
  if v>.01:hits.append({'id':n,'mm3':v})
 return hits
report['static_hits']=collisions(m,{n:a.m for n,a in ss.items() if n!='Display_Frame'})
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  moving=m.transform(np.array(rigidtr(yaw,pitch))[:3,:])
  targets={n:a.m.transform(np.array(rigidtr(yaw,0))[:3,:]) if a.group=='yaw' else a.m for n,a in ss.items() if a.group!='pitch'}
  hits=collisions(moving,targets)
  if hits:report['motion_hits'].append({'yaw':yaw,'pitch':pitch,'hits':hits})
for sign in [-1,1]:
 for rel in s['face_joint_z_from_head_mm']:
  n=f'Face_Joint_{sign}_{rel:.1f}_Nut';a=ss[n]
  for d in np.arange(0,10.01,.5):
   v=max(0,(a.m.translate([-sign*float(d),0,0])^m).volume())
   if v>.01:report['side_nut_insertion_hits'].append({'id':n,'travel_mm':float(d),'mm3':v})
for row in lcd:
 f=np.array(row['head_bearing_mm']);axis=np.array(row['axis']);n=row['id']
 bearing=cylinder(f+axis*.03,axis,1.8,.2)-cylinder(f+axis*.02,axis,1.25,.22)
 obstacles={'Display_Frame':m,'Display_PCB':ss['Display_PCB'].m}
 driver=cylinder(f-axis*1.6,-axis,1.5,35)
 entry=[]
 for d in np.arange(0,25.01,.5):
  hits=collisions(ss[n].m.translate((-axis*d).tolist()),obstacles)
  if hits:entry.append({'distance_mm':float(d),'hits':hits})
 report['LCD_checks'].append({'id':n,'missing_bearing_mm3':max(0,(bearing-m).volume()),'driver_hits':collisions(driver,obstacles),'screw_insertion_hits':entry})
report['poses']=130
report['local_result']='PASS' if report['positive_components']==1 and not report['static_hits'] and not report['motion_hits'] and not report['side_nut_insertion_hits'] and all(r['missing_bearing_mm3']<.005 and not r['driver_hits'] and not r['screw_insertion_hits'] for r in report['LCD_checks']) else 'FAIL'
o=obj('Display_Frame');original_material=MATS['frame']
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
local={'Display_Frame','Display_PCB','Pitch_Cradle','Pitch_Servo','Yaw_Servo'}|{n for n in ss if n.startswith(('Face_Joint_','LCD_Mount_Screw'))}
manifest={}
for tag,current in [('previous',previous),('flush',m)]:
 d=current.to_mesh64();inv=o.matrix_world.inverted();me=bpy.data.meshes.new('DisplayFrame_'+tag+'_study')
 me.from_pydata([tuple(inv@Vector(v)) for v in d.vert_properties[:,:3]],[],d.tri_verts.tolist());me.update()
 o.data=me;me.materials.append(original_material);SOLIDS.pop(o.name,None)
 for name,visible,loc,target,scale in [('detail',local,(-94,122,306),(-32,28,222),49),('part',{'Display_Frame'},(105,-155,312),(0,28,238),91)]:
  for ob in sc.objects:
   if ob.type=='MESH':ob.hide_render=ob.name.removeprefix(PREFIX) not in visible
  camera('frame_'+tag+name,loc,target,scale);sc.render.filepath=str(here/(tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
  manifest[tag+'_'+name]={'camera_mm':loc,'target_mm':target,'scale_mm':scale,'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
(here/'flush_render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(here/'flush_candidate.blend'))
report['source_hashes_unchanged']=all(hashlib.sha256((PROJECT/f).read_bytes()).hexdigest()==v for f,v in hashes.items())
(here/'flush_candidate_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FLUSH_CANDIDATE',json.dumps(report),flush=True)
