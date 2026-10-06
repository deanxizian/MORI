"""Sectioned review copies of actual failed rigid/contact study poses."""
from pathlib import Path
THIS=Path(__file__).resolve(); HELPER=THIS.parent/'screen_CAM_complete_head_insertion.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nheadsets=',1)[0],str(HELPER),'exec'),globals())
__file__=str(THIS)
from render import camera
from validate_head_cleanup import geometry_record
REVIEW=OUT/'review';REVIEW.mkdir(exist_ok=True)
before={o.name:geometry_record(o) for o in parts()}
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE','FONT','EMPTY']:o.hide_render=True
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
copies=[]
def mesh(label,m,color):
    a=m.to_mesh64();d=bpy.data.meshes.new('BODY_SUPPLY_'+label);d.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('A8_BODY_SUPPLY_'+label,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('BODY_SUPPLY_MAT_'+label,color,roughness=.58))
    o['study_owner']='A8_BODY_SUPPLY';o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Presentation copy or section only. Do not export as a manufacturing part.';copies.append(o);return o
def hide_copies():
    for o in copies:o.hide_render=True
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=950;sc.render.resolution_percentage=100
sc.render.threads_mode='FIXED';sc.render.threads=4;sc.render.image_settings.file_format='PNG'
images=[]
rigid=json.loads((OUT/'rigid_screen.json').read_text())
row=next(r for r in rigid['rows'] if r['candidate']=='prewired_core_shells_later' and r['stage']=='bridge_seat_shell_held')
failure=row['failures'][0];st=np.array(failure['shell_transform']);ht=np.array(failure['head_transform'])
shell=solids['Body_Upper'].transform(st[:3,:4]);yoke=solids['Pitch_Yoke'].transform(ht[:3,:4])
# A front half-section reveals the checked interference, without altering any
# calculation solid or original Blender object.
section=manifold.Manifold.cube([300,300,400]).translate([-300,-150,0])
mesh('shell_section',shell^section,(.72,.73,.73))
for n in ['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Servo','Pitch_Servo','Load_Frame','MCU_Carrier']:
    T=ht if n in moving else I
    mesh(n,solids[n].transform(T[:3,:4]),(.18,.43,.51) if n in moving else (.53,.54,.55))
hit=shell^yoke;mesh('rigid_collision',hit,(.94,.10,.06))
camera('A8_BODY_SUPPLY_RIGID',(220,-230,270),(0,0,165),170)
sc.render.filepath=str(REVIEW/'head_shell_order_collision.png');bpy.ops.render.render(write_still=True)
images.append(dict(file='head_shell_order_collision.png',sha256=sha(REVIEW/'head_shell_order_collision.png'),
    caption='身体上壳按旧动作抬起，碰到已装的 Pitch_Yoke；红色为实际相交体。外壳作展示剖切。'))
hide_copies()
neck=json.loads((OUT/'neck_contact/screen.json').read_text());fail=neck['rows'][1]['cases'][0]['failures'][0]
T=np.array(fail['transform_3x4']);dims=np.array(neck['rows'][1]['dims'])
contact=manifold.Manifold.cube(dims.tolist(),center=True).transform(T)
er=np.array([2**-.5,2**-.5,0.]);et=np.array([-2**-.5,2**-.5,0.]);ez=np.array([0.,0.,1.])
cutT=np.column_stack([er,ez,et,np.array([0.,0.,150.])-100*et])
half=manifold.Manifold.cube([300,400,200],center=True).transform(cutT)
mesh('neck_section',solids['Yaw_Base']^half,(.48,.55,.59))
mesh('contact_space',contact,(.94,.58,.12))
center=np.array(T[:,3]);eye=center+50*et+3*er+8*ez
camera('A8_BODY_SUPPLY_NECK',eye.tolist(),center.tolist(),17)
sc.render.filepath=str(REVIEW/'larger_contact_neck_section.png');bpy.ops.render.render(write_still=True)
images.append(dict(file='larger_contact_neck_section.png',sha256=sha(REVIEW/'larger_contact_neck_section.png'),
    caption='较大端子预留体在下部弯道的首个间隙不足位置；橙色是预留空间，不是实际端子 CAD。'))
assert all(geometry_record(o)==before[o.name] for o in parts() if o.name in before)
sc['independent_study']='Failed body supply assembly alternatives; review sections only; main unchanged'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(REVIEW/'review.blend'))
report=dict(status='PASS',scope='Images accurately reflect checked study poses; assembly remains BLOCKED',
    script_sha256=sha(THIS),helper_sha256=sha(HELPER),source_main_sha256=source_hash,
    source_rigid_sha256=sha(OUT/'rigid_screen.json'),source_neck_sha256=sha(OUT/'neck_contact/screen.json'),
    images=images,physical_source_objects_preserved=len(before),review_sha256=sha(REVIEW/'review.blend'),
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(REVIEW/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BODY_SUPPLY_REVIEW_DONE',len(images),len(before),flush=True)
