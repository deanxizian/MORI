"""Render the saved assembly at the same camera before/after a local foot change."""
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
if a.tag=='before':
    for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
    bpy.context.view_layer.update()
    o=bpy.data.objects[PREFIX+'Pitch_Yoke'];o.data.calc_loop_triangles()
    save_json(out/'baseline_geometry.json',{'revision':'V1.2-M1.30',
        'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()},
        'Pitch_Yoke':{'vertices_mm':[list(v) for v in vertices_world(o)],
                      'triangles':[list(t.vertices) for t in o.data.loop_triangles]}})
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1050;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
plain=material('foot_review_print',(.18,.31,.35),roughness=.65)
for n in ['Pitch_Yoke','Pitch_Cradle','Display_Frame']:
    o=bpy.data.objects[PREFIX+n];o.data.materials.clear();o.data.materials.append(plain)
head={o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['yaw','pitch']}
head-={'Head_Front','Head_Rear','Head_Lower_Guard','Face_Protector','Camera_Window'}
head|={'Eye_L','Eye_R'}
views={
 'head':(head,(270,190,455),(0,0,219),139),
 'foot':({'Pitch_Yoke'},(104,130,282),(0,18,194),52),
 'side':({'Pitch_Yoke'},(180,20,196),(0,20,196),37),
}
manifest={};mpath=out/(a.tag+'_render_manifest.json')
if a.views!='all' and mpath.exists():manifest=json.loads(mpath.read_text())['views']
for key,(visible,loc,aim,scale) in views.items():
    if a.views!='all' and key not in a.views.split(','):continue
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('foot_review_'+key,loc,aim,scale)
    sc.render.filepath=str(out/(a.tag+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
    manifest[key]={'camera_mm':loc,'target_mm':aim,'ortho_scale_mm':scale,'visible_ids':sorted(visible),
                   'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,
 'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 'geometry_changes_for_render':'NONE','views':manifest})
print('SEAT_FOOT_RENDERED',a.tag,flush=True)
