"""Inspect original LCD connector triangles and reconstructed CAM connector.

Views do not certify a mated interface or replace supplier documentation.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex/connector_faces';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS
from render import camera

ctx=Context();scene=bpy.context.scene;tag='MORI_FFC_FACE_REVIEW__';items=[];records=[]
for objname,ref in [('Display_PCB','Connector_108'),('CAM_Mainboard','DISPLAY_FPC_18')]:
    o=ctx.ss[objname].o
    row=next(x for x in json.loads(o['component_reference_index']) if x['reference']==ref)
    a,b=row['vertices'];f0,f1=row['faces']
    vertices=np.array([o.matrix_world @ o.data.vertices[i].co for i in range(a,b)])
    faces=np.array([[v-a for v in f.vertices] for f in list(o.data.polygons)[f0:f1]],dtype=np.int64)
    assert faces.min()>=0 and faces.max()<len(vertices)
    mesh=bpy.data.meshes.new(tag+ref);mesh.from_pydata(vertices.tolist(),[],faces.tolist());mesh.update()
    copy=bpy.data.objects.new(tag+ref,mesh);scene.collection.objects.link(copy);copy.color=(.8,.79,.7,1)
    copy['robot_part']=False;copy['category']='PURCHASED_REFERENCE';copy['data_status']=row['evidence']
    copy['scope']='Unmodified component triangles for inspection, no mated cable proof.'
    items.append(copy)
    np.savez_compressed(OUT/(ref+'.npz'),vertices_mm=vertices,triangles=faces)
    records.append(dict(object=objname,reference=ref,evidence=row['evidence'],
        vertices=len(vertices),faces=len(faces),bounds_mm=[vertices.min(0).tolist(),vertices.max(0).tolist()]))

for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
scene.display.shading.background_type='WORLD';scene.world.color=(.9,.92,.94)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1500;scene.render.resolution_y=1100
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
images=[]
for o,r in zip(items,records):
    c=np.mean(r['bounds_mm'],axis=0)
    for suffix,direction in [('plus_x',(30,-15,7)),('minus_x',(-30,-15,7)),('back',(0,-40,7))]:
        for x in items:x.hide_render=True
        o.hide_render=False
        name=r['reference']+'_'+suffix
        camera(tag+name,c+direction,c,17)
        scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
        images.append(dict(file=name+'.png',eye_mm=(c+direction).tolist(),target_mm=c.tolist(),sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged()
report=dict(status='PASS',scope='Only unchanged mesh extraction and inspection views',sources=ctx.sources,
    components=records,images=images,main_changed=False,interface_qualification='BLOCKED',
    script_sha256=sha(Path(__file__)))
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FFC_CONNECTOR_FACES_DONE',flush=True)
