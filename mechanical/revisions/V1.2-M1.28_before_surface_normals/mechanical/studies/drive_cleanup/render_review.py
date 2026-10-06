import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
p=argparse.ArgumentParser();p.add_argument('--tag',default='before');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=850;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
mat=material('drive_review_uniform',(.24,.32,.35),roughness=.55)
for n in ['Drive_Bridge','Motor_Retainer','Load_Frame']:
 ob=bpy.data.objects[PREFIX+n];ob.data.materials.clear();ob.data.materials.append(mat)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
assembly={'Load_Frame','Battery_Tray','Battery','Drive_Bridge','Motor_Retainer','Drive_Motor_L','Drive_Motor_R','Wheel_Axle_L','Wheel_Axle_R'}
assembly|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith((PREFIX+'Wheel_Cap_Clamp_',PREFIX+'Drive_L_',PREFIX+'Drive_R_'))}
sets={'assembly':(assembly,(240,320,-145),(0,0,76),154),
      'drive':({'Drive_Bridge'},(200,330,160),(0,0,55),132),
      'cap':({'Motor_Retainer'},(220,340,205),(0,0,42),128),
      'frame':({'Load_Frame','Battery_Tray','Drive_Bridge','Motor_Retainer'},(260,330,-115),(0,0,79),155)}
for name,(ids,loc,aim,scale) in sets.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in ids
 camera(a.tag+'_'+name,loc,aim,scale);sc.render.filepath=str(Path(__file__).parent/(a.tag+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
save_json(Path(__file__).parent/(a.tag+'_render_manifest.json'),{'tag':a.tag,'source_blend':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'method':'Same loaded meshes; visibility and uniform review material only; identical before/after camera settings','views':{name:{'camera':list(spec[1]),'target':list(spec[2]),'scale':spec[3],'sha256':hashlib.sha256((Path(__file__).parent/(a.tag+'_'+name+'.png')).read_bytes()).hexdigest()} for name,spec in sets.items()}})
print('DRIVE_REVIEW_RENDERED',a.tag)
