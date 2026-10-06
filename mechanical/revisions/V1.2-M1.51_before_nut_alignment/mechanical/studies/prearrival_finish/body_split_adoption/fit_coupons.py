"""Extract two actual bottom-joint test coupons, preserving the current model."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];OUT=HERE/'fit_coupons';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,sha
from common import bpy,np,manifold,Vector
from body_shell_split import boxm
from export import write_stl,read_stl,topology
from interface_completion import repair_quantized_triangles
ctx=Context();source_scene=bpy.context.scene
scene=bpy.data.scenes.new('MORI_Body_Seam_Trial_M1_51');scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';sh=scene.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_shadows=True;sh.background_type='WORLD'
scene.world=bpy.data.worlds.new('MORI_BODYFIT_World');scene.world.color=(.9,.93,.94)
rows=[];objects=[]
for n,label in [('Body_Front','Front_Male'),('Body_Rear','Rear_Female')]:
    m=ctx.ss[n].m^boxm([-29,-8,0],[-11,8,35]);assert len(m.decompose())==1
    m=m.translate([20,0,-20]);original=m
    m=m.set_tolerance(.00001).simplify(.00001)
    a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.asarray(a.tri_verts,dtype=np.int64)
    before_topology=topology(v,f);print(label,'quantized topology',before_topology,flush=True)
    v,f,repairs,bad=repair_quantized_triangles(v,f);assert not bad
    repaired=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')))
    assert repaired.status()==manifold.Error.NoError and len(repaired.decompose())==1
    changed_volume=float((original-repaired).volume()+(repaired-original).volume())
    assert changed_volume<.001,(label,changed_volume)
    mesh=bpy.data.meshes.new('MORI_BODYFIT_'+label);mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
    o=bpy.data.objects.new('MORI_BODYFIT_'+label,mesh);scene.collection.objects.link(o);o['category']='PRINTABLE';o['data_status']='ASSUMED';o['mori_owner']='body_seam_fit_coupons_M1_51';o.color=(.55,.78,.85,1) if n=='Body_Front' else (.90,.82,.65,1);objects.append(o)
    path=OUT/(label+'.stl');write_stl(o,path);vv,ff,nn=read_stl(path);t=topology(vv,ff,nn)
    assert all(t[k]==0 for k in ['nonmanifold_edges','boundary_edges','inconsistent_edges','degenerate_triangles','inconsistent_stl_normals']),t
    assert t['signed_volume_mm3']>0
    rows.append(dict(id=label,source=n,file=path.name,sha256=sha(path),topology=t,bounds_mm=list(m.bounding_box()),source_clip_mm=[[-29,-8,0],[-11,8,35]],translation_only_mm=[20,0,-20],scale=1,quantized_topology_before_repair=before_topology,mesh_repairs=repairs,symmetric_difference_mm3=changed_volume))
# Saved fixture remains in its mating coordinates. Only the preview explodes it.
cdata=bpy.data.cameras.new('MORI_BODYFIT_Camera');cam=bpy.data.objects.new('MORI_BODYFIT_Camera',cdata);scene.collection.objects.link(cam);scene.camera=cam
cam.location=(48,62,54);target=Vector((0,0,9));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cdata.type='ORTHO';cdata.ortho_scale=50
bpy.context.window.scene=scene
bpy.context.view_layer.update()
blend=OUT/'body_seam_trial.blend';bpy.data.libraries.write(str(blend),{scene},fake_user=True)
for o in objects:o.location.y=5 if o.name.endswith('Front_Male') else -5
scene.render.filepath=str(OUT/'preview.png');bpy.ops.render.render(write_still=True)
bpy.context.window.scene=source_scene;ctx.assert_unchanged()
report=dict(status='PASS',scope='Extracted current-geometry sample meshes and STL topology, not physical fit',source_blend_sha256=ctx.source_hash,configuration_sha256=sha(PROJECT/'config/geometry.json'),parts=rows,trial_clearance_mm=.3,fit_status='NOT_TESTED',material='PA12, same process/batch as body shells',image=dict(file='preview.png',sha256=sha(OUT/'preview.png')),editable=dict(file=blend.name,sha256=sha(blend)),main_changed=False,limits='Local clipped shell samples reproduce the joint, not full-shell deformation or strength; no claim of manufacturing acceptance.')
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(OUT/'measurements.csv').write_text('sample_id,print_vendor,material,batch,date,measured_tongue_width_mm,measured_tongue_thickness_mm,measured_socket_width_mm,measured_socket_height_mm,insertion_observation,removal_observation,damage_or_looseness,decision\nM1.51-bottom-joint,,,,,,,,,,,,\n')
(OUT/'README.md').write_text('''# M1.51 底部插舌试配小样

两件样片直接截取当前 Body_Front / Body_Rear 左下方接合处，仅平移坐标，未缩放；不是新增整机零件。

- Front_Male.stl：插舌。
- Rear_Female.stl：接收座。
- STL 单位为 mm，按 1:1 制作；body_seam_trial.blend 保留配对位置。
- 使用与身体壳相同的 PA12 工艺、批次。当前单边间隙为 0.3 mm，接收座名义顶壁/侧壁为 1.7 mm。

到货后先记录尺寸和毛刺情况，再试插、试拔并记录卡滞、松旷和损伤。先保留原打印配合面数据，再讨论修整或改间隙。结果填入 measurements.csv。

局部小样只能验证名义接口配合；不能替代整壳变形、紧固预紧、承载或疲劳试验。没有制造放行或实物验证结论。
''')
(OUT/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>M1.51 底部插舌试片</title><style>body{max-width:980px;margin:30px auto;padding:20px;font:16px/1.75 system-ui;background:#edf2f0;color:#234}img{width:100%}a{color:#167260}</style><a href="../index.html">返回前后分壳</a><h1>底部插舌试配小样</h1><p>两件样片直接取自当前壳体接口。单边试配间隙0.3mm；PA12实际配合尚未验证。</p><img src="preview.png"><p><a href="Front_Male.stl">插舌 STL</a> · <a href="Rear_Female.stl">接收座 STL</a> · <a href="body_seam_trial.blend">配对 Blender</a> · <a href="README.md">试配说明</a> · <a href="measurements.csv">测量记录表</a></p><p>局部小样不代表整壳强度、变形或制造验收。</p></html>''')
print('BODY_SEAM_COUPONS_PASS',flush=True)
