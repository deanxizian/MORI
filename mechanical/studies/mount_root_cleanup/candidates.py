import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from monocoque_structure import obj,source_build
from render import camera
from layout_cleanup import mm_mesh
from microphone_geometry import microphone_paths
study=Path(__file__).parent
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();source_build().materials();bpy.context.view_layer.update()
records={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
old=Solid(obj('Pitch_Cradle'));d=old.m.to_mesh64()
base={'revision':P['revision'],'parts':records,'Pitch_Cradle':{'vertices_mm':d.vert_properties[:,:3].tolist(),'triangles':d.tri_verts.tolist()}}
(study/'baseline_geometry.json').write_text(json.dumps(base))
opts=json.loads((study/'candidate_options.json').read_text());q=P['assembly_completion']['cam_mount'];h=P['head_print_cleanup'];c=P['waveshare_detail']['cam']
x,y,z=P['layout']['cam_board_center_from_head_mm'];z+=D['head_z'];rear=h['cradle_rear_y_mm'];wall=h['cradle_wall_mm'];back=y-c['pcb_thickness_mm']/2-q['pad_surface_extra_mm'];g=c['hole_grid_mm']/2;s=opts['pad_square_mm'];top=z+g+opts['top_margin_mm'];bottom=D['head_z']+h['cradle_bottom_from_head_mm']
def block(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def beam(a,b,r):
 a=Vector(a);b=Vector(b);v=b-a;tr=Matrix.Translation(a)@v.to_track_quat('Z','Y').to_matrix().to_4x4()
 return manifold.Manifold.cylinder(v.length,r,r,64).transform(np.array(tr)[:3,:])
def set_mesh(m):
 o=obj('Pitch_Cradle');d=m.to_mesh64();inv=o.matrix_world.inverted();verts=[tuple(inv@Vector(v)) for v in d.vert_properties[:,:3]]
 me=bpy.data.meshes.new('MountRootStudy');me.from_pydata(verts,[],d.tri_verts.tolist());me.update();o.data=me;me.materials.append(MATS['frame']);SOLIDS.pop(o.name,None)
 # Study planes remain flat without modifying the saved production file.
 for f in me.polygons:f.use_smooth=False
show={'Pitch_Cradle','CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}|{n for n in records if n.startswith('CAM_Mount_')}
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
reports={}
for option in ['before','upper_beam','full_plate']:
 m=old.m
 if option!='before':
  if option=='upper_beam':m+=block([-opts['upper_beam_width_mm']/2,rear,z+g-s/2],[opts['upper_beam_width_mm']/2,rear+wall,top])
  else:m+=block([-opts['full_plate_width_mm']/2,rear,bottom],[opts['full_plate_width_mm']/2,rear+wall,top])
  for u in [-1,1]:
   for v in [-1,1]:
    xx=x+u*g;zz=z+v*g
    m+=block([xx-s/2,rear+wall-.2,zz-s/2],[xx+s/2,back,zz+s/2])
    m-=beam([xx,back+.1,zz],[xx,back-5,zz],q['pilot_diameter_mm']/2)
  if option=='full_plate':
   for p in microphone_paths():m-=beam(p['start'],p['inner'],opts['acoustic_bore_radius_mm'])
 set_mesh(m)
 collisions=[]
 for o in parts():
  n=o.name.removeprefix(PREFIX)
  if n=='Pitch_Cradle' or o.get('group')=='dock':continue
  a=Solid(o);v=max(0,(m^a.m).volume())
  if v>.01:collisions.append({'id':n,'mm3':v})
 air=[]
 for p in microphone_paths():
  probe=beam(p['start'],p['inner'],.4)+beam(p['inner'],p['outside'],.4)
  air.append({'side':p['side'],'overlap_mm3':max(0,(m^probe).volume())})
 reports[option]={'volume_mm3':m.volume(),'positive_components':sum(p.volume()>.001 for p in m.decompose()),'collisions':collisions,'mic_original_probes':air}
 for view,loc,tgt,scale in [('rear',(70,-125,290),(0,-27,242),62),('front',(55,100,280),(0,-25,240),65)]:
  for o in sc.objects:
   if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in show
  camera(option+view,loc,tgt,scale);sc.render.filepath=str(study/(option+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
(study/'candidate_check.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
print('CANDIDATES_COMPLETE',json.dumps(reports),flush=True)
