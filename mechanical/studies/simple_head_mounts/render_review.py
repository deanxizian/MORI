"""Same saved part geometry and identical cameras for the M1.34 comparison."""
import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera

ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(__file__).parent;sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc
load_collections();assembled();bpy.context.view_layer.update()
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1050;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
for name in ['Pitch_Cradle','Pitch_Yoke']:
    o=bpy.data.objects[PREFIX+name];o.data.materials.clear();o.data.materials.append(material('simple_mount_review',(.18,.31,.35),roughness=.65))
head={o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['yaw','pitch']}
head-=set(['Head_Front','Head_Rear','Yaw_Service_Loop'])
views={
 'head':(head,(170,100,398),(0,0,229),150),
 'lug':({'Pitch_Cradle'},(46.75,3.5,330),(46.75,3.5,247),15),
 'cradle':({'Pitch_Cradle'},(150,125,369),(0,-1,230),124),
 'pads':({'Pitch_Yoke'},(45,30,315),(0,2,200),58),
}
manifest={}
for key,(visible,loc,aim,scale) in views.items():
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
    camera('simple_head_mounts_'+key,loc,aim,scale)
    sc.render.filepath=str(out/(a.tag+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
    manifest[key]={'camera_mm':loc,'target_mm':aim,'ortho_scale_mm':scale,'visible_ids':sorted(visible),'sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest()}
save_json(out/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changes_for_render':'NONE','views':manifest})
print('SIMPLE_HEAD_MOUNTS_RENDERED',a.tag,flush=True)
