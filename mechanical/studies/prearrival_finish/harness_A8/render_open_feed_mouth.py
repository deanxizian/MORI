"""Actual saved meshes, identical cameras, no changes to the main scene."""
from pathlib import Path
import sys,json,hashlib
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from render import camera
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record
from common import mesh as create_mesh
J3=HERE/'assembly_feed_v3';OUT=J3/'open_mouth';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=OUT/'cleaned/candidate.blend';assert Path(bpy.data.filepath)==expected
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
records={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=True
o=physical['Pitch_Yoke'];o.hide_render=False
o.data.materials.clear();o.data.materials.append(material('MOUTH_REVIEW_PA12',(.36,.49,.51),roughness=.65))
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for label,path in [('before',J3/'cleaned/Pitch_Yoke.npz'),('after',OUT/'cleaned/Pitch_Yoke.npz')]:
    data=np.load(path);m=manifold.Manifold(manifold.Mesh64(vert_properties=data['vertices_mm'],tri_verts=data['triangles'].astype(np.uint64)))
    replace_owned('Pitch_Yoke',m)
    camera('MOUTH_COMPARE',(45,65,234),(10.5,10.5,188.5),30)
    dest=OUT/('mouth_'+label+'.png');sc.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    images.append({'file':dest.name,'sha256':sha(dest),'source_mesh':str(path.relative_to(PROJECT)),
        'source_mesh_sha256':sha(path),'camera_eye_mm':[45,65,234],'target_mm':[10.5,10.5,188.5],'ortho_scale_mm':30})
assert all(geometry_record(o)==records[n] for n,o in physical.items() if n!='Pitch_Yoke')
result={'status':'PASS','scope':'Two identical-camera source mesh renders; all other scene parts hidden for feature inspection',
    'source_script_sha256':sha(SCRIPT),'source_main_sha256':sha(PROJECT/'mechanical/mori_v1_2.blend'),
    'source_saved_candidate_sha256':sha(expected),'images':images,'main_applied':False,'geometry_saved':False}
(OUT/'render_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('OPEN_MOUTH_RENDERED',flush=True)
