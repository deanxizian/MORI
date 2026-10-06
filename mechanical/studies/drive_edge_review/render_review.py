"""Identical cameras for original and updated actual cap geometry."""
import sys,argparse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
a=argparse.ArgumentParser();a.add_argument('--tag',default='after');args=a.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(__file__).parent;sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc
load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=800;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
for name,color in [('Drive_Bridge',(.64,.66,.65)),('Motor_Retainer',(.22,.36,.41))]:
 o=bpy.data.objects[PREFIX+name];o.data.materials.clear();o.data.materials.append(material('edge_review_'+name,color,roughness=.7))
sets={'underside':({'Drive_Bridge','Motor_Retainer'},(120,300,-205),(20,0,46),103),
      'cap_close':({'Motor_Retainer'},(120,150,-150),(35,0,44),46)}
manifest={}
for name,(visible,loc,aim,scale) in sets.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('edge_'+args.tag+'_'+name,loc,aim,scale);sc.render.filepath=str(out/(args.tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'file':Path(sc.render.filepath).name,'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest(),'camera_mm':loc,'target_mm':aim,'ortho_scale_mm':scale}
save_json(out/(args.tag+'_render_manifest.json'),{'revision':P['revision'],'tag':args.tag,'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changed_for_render':False,'views':manifest})
