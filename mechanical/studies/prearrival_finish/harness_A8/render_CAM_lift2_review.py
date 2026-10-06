"""Show the actual upstream collision and the verified board-only descent."""
from pathlib import Path
LV_SCRIPT=Path(__file__).resolve();LV_ROOT=LV_SCRIPT.parent
LV_HELPER=LV_ROOT/'render_CAM_forming_contact_review.py';__file__=str(LV_HELPER)
exec(compile(LV_HELPER.read_text().split('\nscene=bpy.context.scene;',1)[0],str(LV_HELPER),'exec'),globals())
__file__=str(LV_SCRIPT)
LV_OUT=FM_OUT/'lifted_end2';lv_source=json.loads((LV_OUT/'screen.json').read_text())
lv_collision=json.loads((LV_OUT/'packing_collision_witness.json').read_text())
lv_board=json.loads((LV_OUT/'board_descent_continuous.json').read_text())
assert lv_collision['status']=='FAIL' and lv_board['status']=='PASS'
fr_lengths[:]=lv_source['segment_lengths_mm'];fm_lengths[:]=fr_lengths
fm_core_length=lv_source['core_parameter_mm'];fm_tail_parameter=lv_source['tail_parameter_mm']
lv_extra=[];lv_images=[]


def lv_wire(name,p,color):
    d=bpy.data.curves.new('A8_LIFT2_'+name,'CURVE');d.dimensions='3D';d.bevel_depth=OD/2.;d.bevel_resolution=4;d.use_fill_caps=True
    sp=d.splines.new('POLY');sp.points.add(len(p)-1)
    for q,v in zip(sp.points,p):q.co=(*v,1.)
    o=bpy.data.objects.new('A8_LIFT2_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_LIFT2_MAT_'+name,color,roughness=.38));lv_extra.append(o)
    o['study_owner']='CAM_LIFT2_REVIEW';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    return o


def lv_capture(name,eye,target,scale,scope):
    camera('A8_LIFT2_CAMERA',eye,target,scale);scene.render.filepath=str(LV_OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    lv_images.append({'file':name+'.png','sha256':sha(LV_OUT/(name+'.png')),'scope':scope})


scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
base=vt_pose(.8,9.,False)
for o in vt_objects+vt_moving:o.hide_render=True
lv_wire('moving_wire_0',base,(.05,.58,.67));lv_wire('upstream_wire_1',pw_fans[1][0],(.9,.22,.06))
target=(np.asarray(lv_collision['wire_point_mm'])+lv_collision['upstream_point_mm'])/2.
lv_capture('upstream_collision',target+[12.,-17.,9.],target,7.,'Isolated two nominal wires at fraction0.8; their documented radius envelopes intersect')
for o in lv_extra:o.hide_render=True
for o in vt_objects:o.hide_render=False
vt_pose(1.,9.,False)
# Remove bare-contact boxes after the comparison; installed housing details
# are a catalogue allocation, while actual contact insertion remains open.
for o in vt_moving:
    if 'SSH_BOX' in o.name:o.hide_render=True
board_objects=[]
for n,m in bl_board.items():board_objects.append(vt_mesh(n,m,(.1,.36,.22)))
plug=vt_mesh('LIFT2_catalogue_housing',bl_plug.translate([0.,0.,2.]),(.86,.60,.20))
for h,label in [(8.,'board_at8'),(2.,'board_at2')]:
    for o in board_objects:o.location.z=h
    lv_capture(label,(-90,80,291),(-8,-13,234),92.,f'CAM board at+{h:g}mm with catalogue plug and wires at+2mm; presentation copies only')
assert all(geometry_record(o)==vt_source[o.name] for o in parts() if o.name in vt_source)
scene['independent_study']='Board descent verified in nominal allocation; forming collision unresolved. No physical or manufacturing qualification.'
bpy.ops.wm.save_as_mainfile(filepath=str(LV_OUT/'review.blend'))
(LV_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(LV_SCRIPT),'helper_sha256':sha(LV_HELPER),
    'source_main_sha256':source_hash,'source_collision_witness_sha256':sha(LV_OUT/'packing_collision_witness.json'),
    'source_board_descent_sha256':sha(LV_OUT/'board_descent_continuous.json'),'images':lv_images,
    'physical_source_objects_preserved':len(vt_source),'review_sha256':sha(LV_OUT/'review.blend'),
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LIFT2_REVIEW_RENDER_DONE',len(lv_images),flush=True)
