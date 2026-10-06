"""Localize the camera-end obstruction without altering its capture geometry."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex/camera_corridor'; OUT=BASE/'entry'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS,manifold,Vector
from render import camera
ctx=Context(); name='R3_F3_O1.8_W6.6'; path=BASE/(name+'.npz'); data=np.load(path)
m=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles']))
frame=ctx.ss['Display_Frame']; hit=m^frame.m; h=hit.to_mesh64(); v=np.asarray(h.vert_properties[:,:3])
report=dict(status='PASS',scope='Diagnostic localization only, route remains blocked',sources=ctx.sources,
    inputs={str(path.relative_to(ROOT)):sha(path)},candidate=name,
    frame_overlap_mm3=float(hit.volume()),overlap_bounds_mm=[v.min(0).tolist(),v.max(0).tolist()],
    route_end_mm=data['points_mm'][-1].tolist(),end_to_frame_distance_mm=float(ctx.targets['Display_Frame']['tree'].find_nearest(Vector(data['points_mm'][-1]))[3]),
    last_20mm_center_samples=[dict(point_mm=p.tolist(),frame_surface_distance_mm=float(ctx.targets['Display_Frame']['tree'].find_nearest(Vector(p))[3])) for p in data['points_mm'][-130::10]],
    main_changed=False,adopted=False,route_status='BLOCKED',script_sha256=sha(Path(__file__)))
scene=bpy.context.scene; tag='MORI_CAMERA_ENTRY_REVIEW__'; copies=[]
def mesh(n,verts,faces,color):
    me=bpy.data.meshes.new(tag+n); me.from_pydata(np.asarray(verts).tolist(),[],np.asarray(faces).tolist()); me.update()
    o=bpy.data.objects.new(tag+n,me); scene.collection.objects.link(o); o.color=color; copies.append(o)
    o['robot_part']=False; o['category']='PLACEHOLDER'; o['data_status']='ASSUMED'
    return o
for n in ['Display_Frame','Camera_PCB','Camera_Lens','CAM_Mainboard','Pitch_Servo','Yaw_Servo']:
    s=ctx.ss[n]; mesh(n,s.v,s.f,(.61,.67,.71,1) if n!='CAM_Mainboard' else (.18,.38,.3,1))
mesh('FPC_capacity',data['vertices_mm'],data['triangles'],(.96,.56,.08,1))
mesh('overlap',v,h.tri_verts,(1,.05,.08,1))
for col in COLS.values(): col.hide_render=False; col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']: o.hide_render=True; o.hide_set(True)
for o in copies: o.hide_render=False; o.hide_set(False)
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.color_type='OBJECT'
scene.display.shading.light='STUDIO'; scene.display.shading.show_cavity=False
scene.display.shading.background_type='WORLD'; scene.world.color=(.91,.93,.95)
scene.view_settings.view_transform='Standard'; scene.render.resolution_x=1500; scene.render.resolution_y=1100
scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
for suffix,eye,target,scale in [('side',(-120,8,264),(0,4,247),78),('entry',(-70,58,283),(0,25,262),27)]:
    camera(tag+suffix,eye,target,scale); scene.render.filepath=str(OUT/(suffix+'.png')); bpy.ops.render.render(write_still=True)
ctx.assert_unchanged()
blend=OUT/'MORI_M1_49_camera_FPC_entry_review.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend)); ctx.assert_unchanged()
report.update(blend=blend.name,blend_sha256=sha(blend),images={n:sha(OUT/n) for n in ['side.png','entry.png']})
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAMERA_FPC_ENTRY_REVIEW_DONE',report['overlap_bounds_mm'],flush=True)
