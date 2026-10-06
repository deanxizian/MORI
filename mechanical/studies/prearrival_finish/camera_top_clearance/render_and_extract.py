"""Render the saved candidate and extract actual local mesh sections."""
import sys,json,hashlib
from pathlib import Path
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((OUT/'construction.json').read_text());v=json.loads((OUT/'verification.json').read_text())
assert v['status']=='PASS' and sha(OUT/'candidate.blend')==v['candidate_sha256']
load_collections()
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[c].hide_viewport=False
assembled();bpy.context.view_layer.update()
objs={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
rc=np.array(j['camera_local_basis_columns']);p=np.array(j['camera_pupil_world_mm'])
def cached(name):
    a=np.load(OUT/name)
    return manifold.Manifold(manifold.Mesh64(np.array(a['vertices_mm'],copy=True),np.array(a['triangles'],dtype=np.uint64,copy=True)))
old=cached('original_Display_Frame.npz');new=Solid(objs['Display_Frame']).m;removed=cached('removed.npz')
solids=dict(original=old,candidate=new,removed=removed,
    shell=Solid(objs['Head_Front']).m,camera=Solid(objs['Camera_PCB']).m+Solid(objs['Camera_Lens']).m)
Q=np.array([[0.,0,1],[0,-1,0],[1,0,0]]);A=Q@np.linalg.inv(rc);tr=np.column_stack([A,-A@p])
sections={}
for x in [0.,6.]:
    sections[str(x)]={n:[a.tolist() for a in m.transform(tr).slice(x).to_polygons()] for n,m in solids.items()}
(OUT/'sections.json').write_text(json.dumps(dict(script_sha256=sha(SCRIPT),candidate_sha256=sha(OUT/'candidate.blend'),verification_sha256=sha(OUT/'verification.json'),plane='camera local X; plot horizontal W toward lens, vertical -V toward pocket top',sections=sections),ensure_ascii=False,indent=2)+'\n')

sc=bpy.context.scene
for o in sc.objects:o.hide_render=True
for n,col in [('Display_Frame',(.38,.50,.54,1)),('Camera_PCB',(.65,.34,.12,1)),('Camera_Lens',(.04,.055,.07,1))]:
    o=objs[n];o.hide_render=False;o.hide_set(False);o.color=col
frame=objs['Display_Frame'];saved_mesh=frame.data
def mesh_of(m,name):
    r=m.to_mesh64();me=bpy.data.meshes.new(name);me.from_pydata(r.vert_properties[:,:3].tolist(),[],r.tri_verts.tolist());me.update();return me
rm=bpy.data.objects.new('CAMTOP_removed_reference',mesh_of(removed,'removed_render'));sc.collection.objects.link(rm);rm.color=(.85,.20,.075,1)
camdata=bpy.data.cameras.new('CAMTOP_review_camera');cam=bpy.data.objects.new('CAMTOP_review_camera',camdata);sc.collection.objects.link(cam)
target=Vector(p+rc@np.array([0,-1.5,-2.]));cam.location=p+rc@np.array([22,-20,38.])
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=23
camdata.clip_start=.1;camdata.clip_end=1000;sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='OBJECT';sc.display.shading.light='STUDIO'
sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.show_shadows=True
sc.display.shading.show_specular_highlight=False;sc.display.shading.background_type='WORLD';sc.world.color=(.78,.81,.83)
sc.view_settings.view_transform='Standard';sc.render.film_transparent=False
sc.render.resolution_x=960;sc.render.resolution_y=800;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for name,m in [('before',old),('after',new)]:
    frame.data=mesh_of(m,'CAMTOP_'+name);frame.matrix_world=Matrix.Identity(4);rm.hide_render=name!='before'
    bpy.context.view_layer.update();sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
frame.data=saved_mesh
report=dict(status='PASS',script_sha256=sha(SCRIPT),candidate_sha256=sha(OUT/'candidate.blend'),verification_sha256=sha(OUT/'verification.json'),
    outputs={n:sha(OUT/n) for n in ['before.png','after.png','sections.json']},main_applied=False)
(OUT/'render.json').write_text(json.dumps(report,indent=2)+'\n')
assert all(sha(PROJECT/k)==h for k,h in j['protected_sources'].items())
print('CAMERA_TOP_RENDERED',flush=True)
