"""Fixed-camera views of the real saved print meshes and their display normals."""
import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
p=argparse.ArgumentParser();p.add_argument('--tag',default='after');p.add_argument('--trial',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(__file__).parent
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
if a.trial:
    from head_surface_display import apply_head_surface_display
    apply_head_surface_display()
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True
sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
mat=material('surface_diagnosis',(.24,.32,.35),roughness=.55)
for name in ['Pitch_Cradle','Pitch_Yoke','Display_Frame']:
    o=bpy.data.objects[PREFIX+name];o.data.materials.clear();o.data.materials.append(mat)
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
views={'cradle':('Pitch_Cradle',(240,240,320),(43,2,231),68),
       'yoke':('Pitch_Yoke',(220,340,285),(0,-7,194),130),
       'front_seat':('Pitch_Yoke',(150,330,238),(0,20,194),62)}
for key,(name,loc,aim,scale) in views.items():
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name!=PREFIX+name
    camera('surface_'+key,loc,aim,scale);sc.render.filepath=str(out/(a.tag+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
save_json(out/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
          'mode':'normal-only trial' if a.trial else 'saved model unchanged',
          'views':{k:{'camera':v[1],'target':v[2],'scale':v[3],'sha256':hashlib.sha256((out/(a.tag+'_'+k+'.png')).read_bytes()).hexdigest()} for k,v in views.items()}})
print('HEAD_SURFACE_RENDERED',a.tag)
