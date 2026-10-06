"""Locate actual intersections of two failed free-span candidates."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex/full_route';OUT=BASE/'obstructions'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS,manifold
from render import camera
ctx=Context();scene=bpy.context.scene;tag='MORI_FFC_OBSTRUCTION__';copies=[]
def mesh(name,v,f,color):
    me=bpy.data.meshes.new(tag+name);me.from_pydata(np.asarray(v).tolist(),[],np.asarray(f).tolist());me.update()
    o=bpy.data.objects.new(tag+name,me);scene.collection.objects.link(o);o.color=color
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';copies.append(o);return o
for name,s in ctx.ss.items():
    if s.group in ['pitch','yaw'] and name not in ['Head_Front','Head_Rear']:
        mesh(name,s.v,s.f,(.55,.63,.67,1) if name not in ['CAM_Mainboard','Display_PCB'] else (.13,.35,.27,1))
for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True;o.hide_set(True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=False;scene.display.shading.show_shadows=True
scene.display.shading.background_type='WORLD';scene.world.color=(.91,.93,.95)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1600;scene.render.resolution_y=1200
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
native=list(copies);rows=[];images=[];inputs={}
for folder,case in [('screen','R7.5_W10.5_M15'),('tail_screen','T10.5_W10.5_M15')]:
    path=BASE/folder/(case+'.npz');data=np.load(path);inputs[str(path.relative_to(ROOT))]=sha(path)
    ribbon=mesh(case,data['vertices_mm'],data['triangles'],(.95,.53,.12,1));m=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles']))
    collisions=[];red=[]
    for name in ['Pitch_Yoke','Pitch_Servo','Display_Frame','Head_Front']:
        inter=m^ctx.ss[name].m;v=inter.volume()
        if v<1e-7:continue
        d=inter.to_mesh64();points=np.asarray(d.vert_properties[:,:3]);bounds=[points.min(0).tolist(),points.max(0).tolist()]
        red.append(mesh(case+'_overlap_'+name,points,d.tri_verts,(.95,.05,.08,1)))
        collisions.append(dict(part=name,overlap_mm3=float(v),bounds_mm=bounds))
    for o in copies:o.hide_render=True;o.hide_set(True)
    for o in native+[ribbon]+red:o.hide_render=False;o.hide_set(False)
    for suffix,eye,target,scale in [('above',(-125,135,345),(0,9,233),106),('side',(-150,10,258),(-6,10,230),100)]:
        camera(tag+case+suffix,eye,target,scale)
        file=case+'_'+suffix+'.png';scene.render.filepath=str(OUT/file);bpy.ops.render.render(write_still=True)
        images.append(dict(file=file,case=case,sha256=sha(OUT/file)))
    rows.append(dict(case=case,intersections=collisions))
ctx.assert_unchanged()
blend=OUT/'MORI_M1_49_FFC_failed_route_review.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
result=dict(status='PASS',scope='Failure localization and review views, not cable fit',sources=ctx.sources,
    inputs=inputs,rows=rows,images=images,blend=blend.name,blend_sha256=sha(blend),
    main_changed=False,free_span_fit='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FFC_OBSTRUCTION_REVIEW_DONE',flush=True)
