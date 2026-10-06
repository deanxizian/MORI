"""Show the four real-diameter upper leads before and after lateral seating."""
from pathlib import Path
RV_SCRIPT=Path(__file__).resolve();RV_ROOT=RV_SCRIPT.parent
RV_HELPER=RV_ROOT/'render_CAM_contact_refined_forming.py';__file__=str(RV_HELPER)
exec(compile(RV_HELPER.read_text().split('\nscene=bpy.context.scene;',1)[0],str(RV_HELPER),'exec'),globals())
__file__=str(RV_SCRIPT)
RV_OUT=OR_OUT/'root_seating/aligned_tails'
rv_screen=json.loads((RV_OUT/'screen.json').read_text());assert rv_screen['status']=='PASS'
rv_arrays=np.load(RV_OUT/'curves.npz');rv_objects=[]
for o in bpy.context.scene.objects:
    if o.name in ['A8_ORDER_CAM_Tie_Head','A8_ORDER_CAM_Tie_Band'] or o.name.startswith('A8_ORDER_upstream_'):
        o.hide_render=True;o.hide_viewport=True
for slot in range(4):or_wire(f'root_fixed_body_{slot}',body_samples[slot+1,0][0],or_colors[slot])


def rv_pose(offset):
    for o in rv_objects:bpy.data.objects.remove(o,do_unlink=True)
    rv_objects.clear()
    for slot in range(4):
        p=rv_arrays[f'offset{offset:g}_slot{slot}']
        rv_objects.append(or_wire(f'root_seating_{slot}',p,or_colors[slot]))
        _,tr=ft_frame(0.,p[-1]);rv_objects.append(or_mesh(f'root_seating_terminal_{slot}',ft_box.transform(tr),(.87,.62,.24)))


scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1150;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=4
rv_images=[]
for label,offset,eye,target,scale in [
    ('before_seating',1.5,(30,70,261),(-8,-1.0,231.9),24),
    ('seated',0.,(30,70,261),(-8,-1.0,231.9),24),
    ('complete_leads',1.5,(100,160,365),(-7,0,277),193)]:
    rv_pose(offset);camera('A8_ROOT_SEATING_CAMERA',eye,target,scale)
    scene.render.filepath=str(RV_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    rv_images.append(dict(file=label+'.png',sha256=sha(RV_OUT/(label+'.png')),offset_y_mm=offset,
        all_four_upper_leads_and_contacts_present=True,wire_diameter_mm=OD,
        uninstalled_root_tie_parts=['CAM_Tie_Band','CAM_Tie_Head']))
assert all(geometry_record(o)==or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study']='Lateral four-wire seating before the root tie is fitted; initial feeding, tie wrapping and physical handling are unverified'
scene.render.use_file_extension=True;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(RV_OUT/'review.blend'))
(RV_OUT/'render_manifest.json').write_text(json.dumps(dict(status='PASS',script_sha256=sha(RV_SCRIPT),
    helper_sha256=sha(RV_HELPER),source_main_sha256=source_hash,source_screen_sha256=sha(RV_OUT/'screen.json'),
    source_curves_sha256=sha(RV_OUT/'curves.npz'),physical_source_objects_preserved=len(or_source),images=rv_images,
    review_sha256=sha(RV_OUT/'review.blend'),main_applied=False,whole_harness='BLOCKED',manufacturing_release=False),ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ROOT_SEATING_RENDER_DONE',len(rv_images),flush=True)
