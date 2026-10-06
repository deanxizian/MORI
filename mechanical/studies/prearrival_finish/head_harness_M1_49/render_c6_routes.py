"""Preview only a completed C6 nine-wire candidate proof; never modify main."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes/c6_left_slot_entry'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from render import camera
ctx=Context();report=json.loads((OUT/'combined/lower_nine_screen.json').read_text())
assert report['status']=='PASS' and not report['approved']
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
curves_file=OUT/'combined/lower_nine_candidates.npz';assert sha(curves_file)==report['curve_sha256']
curves=np.load(curves_file);candidate=np.load(OUT/'Yaw_Base_candidate.npz');tag='MORI_C6_ENTRY_REVIEW__'
mesh=bpy.data.meshes.new(tag+'Mesh');mesh.from_pydata(candidate['vertices_mm'].tolist(),[],candidate['triangles'].tolist());mesh.update()
body=bpy.data.objects.new(tag+'Yaw_Base_CANDIDATE',mesh);bpy.context.scene.collection.objects.link(body)
body.color=(.5,.62,.67,1);body['category']='PRINTABLE';body['data_status']='ASSUMED';body['robot_part']=False;body['approved']=False
new=[body]
for row in report['selected']:
    name=row['endpoint'];points=curves[name+'_y0'];cu=bpy.data.curves.new(tag+name,'CURVE');cu.dimensions='3D';cu.bevel_depth=row['OD_mm']/2;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
    for v,p in zip(sp.points,points):v.co=(*p,1)
    o=bpy.data.objects.new(tag+name,cu);bpy.context.scene.collection.objects.link(o)
    o.color=(1.,.68,.06,1) if name.startswith('CAM') else (.84,.17,.09,1) if 'J18' in name else (.95,.36,.08,1)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['robot_part']=False;o['scope']='Unselected wire reference; partial lower route, upper terminals/anchors unfinished'
    new.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
scene.display.shading.show_specular_highlight=False;scene.display.shading.background_type='WORLD';scene.world.color=(.82,.86,.88)
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False;scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';images=[]
for name,eye,target,scale in [('body_entry_rear',(135,-170,205),(0,-12,158),100),('body_entry_under',(130,-170,108),(0,-7,146),90)]:
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n in ['Yaw_Bearing','Yaw_Anti_Lift_Keeper','Power_Module','MCU_Carrier']:
        ctx.ss[n].o.hide_render=False
    for o in new:o.hide_render=False;o.hide_set(False)
    for port in ['motion_J5','power_J9','power_J18']:
        ctx.plug[port].o.hide_render=False;ctx.plug[port].o.color=(.8,.8,.75,1)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_C6_entry_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
result=dict(status='PASS',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'combined/lower_nine_screen.json',curves_file,OUT/'Yaw_Base_candidate.npz']},
    images=images,blend_sha256=sha(blend),scope='Unapproved partial harness preview. Body and head shells hidden for inspection; complete harness, anchors and wired assembly remain incomplete.',
    main_changed=False,approved=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'render_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print('C6_ROUTES_RENDERED',flush=True)
