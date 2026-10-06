import sys,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--tag',default='before');a=p.parse_args(args)
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
mat=material('head_review_uniform',(.24,.32,.35),roughness=.55)
for n in ['Pitch_Cradle','Display_Frame','Pitch_Yoke']:
 ob=bpy.data.objects[PREFIX+n];ob.data.materials.clear();ob.data.materials.append(mat)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
sets={'head':({'Pitch_Cradle','Display_Frame','Pitch_Yoke','Display_PCB','Yaw_Servo','Pitch_Servo','CAM_Mainboard','Camera_PCB','Camera_Lens','Eye_L','Eye_R','Face_Mask','Yaw_Reaction_Link','Pitch_Bearing_L','Pitch_Bearing_R'},(220,350,360),(0,0,225),146),
'cradle':({'Pitch_Cradle'},(210,-330,360),(0,-2,232),125),
'fork':({'Display_Frame'},(200,350,350),(0,28,237),117),
'yoke':({'Pitch_Yoke'},(220,340,285),(0,-7,194),130)}
for name,(ids,loc,aim,scale) in sets.items():
 for ob in sc.objects:
  if ob.type=='MESH':ob.hide_render=ob.name.removeprefix(PREFIX) not in ids
 camera(a.tag+'_'+name,loc,aim,scale)
 sc.render.filepath=str(Path(__file__).parent/(a.tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('HEAD_REVIEW_RENDERED',a.tag)
