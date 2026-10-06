"""Review images of the new ordered-feed recovery, from checked curves."""
from pathlib import Path
OFV_SCRIPT=Path(__file__).resolve();OFV_ROOT=OFV_SCRIPT.parent
OFV_HELPER=OFV_ROOT/'render_CAM_contact_refined_forming.py';__file__=str(OFV_HELPER)
exec(compile(OFV_HELPER.read_text().split('\nscene=bpy.context.scene;',1)[0],str(OFV_HELPER),'exec'),globals())
__file__=str(OFV_SCRIPT)
OFV_OUT=OR_OUT/'root_seating/ordered_feed_recovery'
ofv_report=json.loads((OFV_OUT/'screen.json').read_text());assert ofv_report['status']=='PASS'
ofv_arrays=np.load(OFV_OUT/'curves.npz');ofv_objects=[]
ofv_dims=np.array(ofv_report['terminal_space_allocation_mm'])
ofv_box=manifold.Manifold.cube(ofv_dims,center=True)
for o in bpy.context.scene.objects:
    if o.name in ['A8_ORDER_CAM_Tie_Head','A8_ORDER_CAM_Tie_Band'] or o.name.startswith('A8_ORDER_upstream_'):
        o.hide_render=True;o.hide_viewport=True
for slot in range(4):or_wire(f'ordered_fixed_body_{slot}',body_samples[slot+1,0][0],or_colors[slot])


def ofv_pose(fraction):
    for o in ofv_objects:bpy.data.objects.remove(o,do_unlink=True)
    ofv_objects.clear()
    for slot in range(4):
        p=ofv_arrays[f'f{fraction:g}_slot{slot}']
        ofv_objects.append(or_wire(f'ordered_recovery_{slot}',p,or_colors[slot]))
        terminal=ofv_box.translate((p[-1]+[0.,0.,ofv_dims[2]/2.]).tolist())
        ofv_objects.append(or_mesh(f'ordered_terminal_space_{slot}',terminal,(.87,.62,.24)))


scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1150;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=4
ofv_images=[]
for label,fraction,eye,target,scale in [
    ('after_feed',0.,(100,160,365),(-7,0,270),183),
    ('ready_to_seat',1.,(100,160,365),(-7,0,270),183),
    ('root_detail',1.,(55,105,265),(-7,-1,221),62)]:
    ofv_pose(fraction);camera('A8_ORDERED_FEED_CAMERA',eye,target,scale)
    scene.render.filepath=str(OFV_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    ofv_images.append(dict(file=label+'.png',fraction=fraction,sha256=sha(OFV_OUT/(label+'.png'))))
assert all(geometry_record(o)==or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study']='Ordered CAM feed and recovery; finite checks only, source parts preserved'
scene['terminal_geometry']='ASSUMED 1 x 1.8 x 4.1 mm requested space, not complete vendor geometry'
scene.render.use_file_extension=True;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OFV_OUT/'review.blend'))
report=dict(status='PASS',script_sha256=sha(OFV_SCRIPT),helper_sha256=sha(OFV_HELPER),
    source_main_sha256=source_hash,source_screen_sha256=sha(OFV_OUT/'screen.json'),
    source_curves_sha256=sha(OFV_OUT/'curves.npz'),images=ofv_images,
    physical_source_objects_preserved=len(or_source),review_sha256=sha(OFV_OUT/'review.blend'),
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(OFV_OUT/'render_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ORDERED_FEED_RECOVERY_RENDER_DONE',len(ofv_images),flush=True)
