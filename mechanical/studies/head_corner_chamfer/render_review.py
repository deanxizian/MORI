import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
p=argparse.ArgumentParser();p.add_argument('--tag',default='after');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
mat=material('corner_review_uniform',(.24,.32,.35),roughness=.55)
for n in ['Pitch_Cradle','Display_Frame','Pitch_Yoke']:
 o=bpy.data.objects[PREFIX+n];o.data.materials.clear();o.data.materials.append(mat)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
hz=D['head_z']
head={'Pitch_Cradle','Display_Frame','Pitch_Yoke','Display_PCB','Yaw_Servo','Pitch_Servo','CAM_Mainboard','Camera_PCB','Camera_Lens','Eye_L','Eye_R','Face_Mask','Yaw_Reaction_Link','Pitch_Bearing_L','Pitch_Bearing_R'}
sets={'head':(head,(230,320,hz+205),(0,0,hz),145),
      'cradle':({'Pitch_Cradle'},(210,-330,hz+250),(0,-2,hz),114),
      'corner':({'Pitch_Cradle'},(100,-190,hz+135),(35,-22,hz+7),50)}
for name,(ids,loc,aim,scale) in sets.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in ids
 camera(a.tag+'_'+name,loc,aim,scale);sc.render.filepath=str(Path(__file__).parent/(a.tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
save_json(Path(__file__).parent/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'method':'Same loaded geometry; uniform materials and visibility only','views':{name:{'camera':list(spec[1]),'target':list(spec[2]),'scale':spec[3],'sha256':hashlib.sha256((Path(__file__).parent/(a.tag+'_'+name+'.png')).read_bytes()).hexdigest()} for name,spec in sets.items()}})
print('HEAD_CORNER_RENDERED',a.tag)
