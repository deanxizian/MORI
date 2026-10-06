"""Unmodified saved geometry, identical cameras, and an immutable M1.31 baseline."""
import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record

p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--views',default='all')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(__file__).parent
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
bpy.context.view_layer.update()
if a.tag=='before':
    o=bpy.data.objects[PREFIX+'Pitch_Yoke'];o.data.calc_loop_triangles()
    save_json(out/'baseline_geometry.json',{'revision':'V1.2-M1.31',
        'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()},
        'Pitch_Yoke':{'vertices_mm':[list(v) for v in vertices_world(o)],
                      'triangles':[list(t.vertices) for t in o.data.loop_triangles]}})
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
plain=material('pad_review_print',(.18,.31,.35),roughness=.65)
o=bpy.data.objects[PREFIX+'Pitch_Yoke'];o.data.materials.clear();o.data.materials.append(plain)
hardware={'Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Reaction_Link'}
hardware|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Head_Yaw_Ear_')}
views={
 'pads':({'Pitch_Yoke'},(45,30,315),(0,2,200),58),
 'rear':({'Pitch_Yoke'},(-60,-62,249),(0,-10,200),34),
 'mounted':({'Pitch_Yoke'}|hardware,(120,135,309),(0,0,207),100),
 'yoke':({'Pitch_Yoke'},(145,190,340),(0,0,207),124),
}
manifest={}
for key,(visible,loc,aim,scale) in views.items():
    if a.views!='all' and key not in a.views.split(','):continue
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('pad_review_'+key,loc,aim,scale)
    sc.render.filepath=str(out/(a.tag+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
    manifest[key]={'camera_mm':loc,'target_mm':aim,'ortho_scale_mm':scale,'visible_ids':sorted(visible),
                   'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,
 'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 'geometry_changes_for_render':'NONE','views':manifest})
print('YAW_PAD_RENDERED',a.tag,flush=True)
