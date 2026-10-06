"""Show the verified intermediate wire intersection without altering main."""
from pathlib import Path
CR_SCRIPT=Path(__file__).resolve();CR_ROOT=CR_SCRIPT.parent
CR_HELPER=CR_ROOT/'render_CAM_contact_refined_forming.py';__file__=str(CR_HELPER)
exec(compile(CR_HELPER.read_text().split('\nscene=bpy.context.scene;',1)[0],str(CR_HELPER),'exec'),globals())
__file__=str(CR_SCRIPT)
CR_OUT=OR_OUT/'continuous';cr_diag=json.loads((CR_OUT/'first_failure_segment_distance.json').read_text())
assert cr_diag['real_intersection']=='FAIL'
cr_f=cr_diag['fraction'];cr_amp,cr_angle=cr_diag['controls']
or_path['stages'][3]['path'].append({'fraction':cr_f,'amplitude_mm':cr_amp,'side_angle_deg':cr_angle})
or_pose(3,cr_f)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=4
cr_images=[]
camera('A8_RETURN_CONFLICT',(-105,125,280),(-8,6,219),95)
scene.render.filepath=str(CR_OUT/'conflict_context.png');bpy.ops.render.render(write_still=True)
cr_images.append({'file':'conflict_context.png','sha256':sha(CR_OUT/'conflict_context.png'),'scope':'All four free wires and contacts; shown structure subset'})
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=o.name not in ['A8_ORDER_free_0','A8_ORDER_upstream_1']
target=np.mean(cr_diag['closest']['points_mm'],axis=0)
camera('A8_RETURN_CONFLICT',target+np.array([-24.,26.,18.]),target,10.)
scene.render.filepath=str(CR_OUT/'conflict_closeup.png');bpy.ops.render.render(write_still=True)
cr_images.append({'file':'conflict_closeup.png','sha256':sha(CR_OUT/'conflict_closeup.png'),'scope':'Only the two intersecting wires shown; no geometric enlargement of wire OD'})
assert all(geometry_record(o)==or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study']='Verified intermediate wire-envelope intersection; source path is not installable as prescribed.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(CR_OUT/'conflict_review.blend'))
(CR_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(CR_SCRIPT),'helper_sha256':sha(CR_HELPER),
    'source_main_sha256':source_hash,'source_diagnosis_sha256':sha(CR_OUT/'first_failure_segment_distance.json'),
    'images':cr_images,'physical_source_objects_preserved':len(or_source),'review_sha256':sha(CR_OUT/'conflict_review.blend'),
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('RETURN_CONFLICT_RENDER_DONE',flush=True)
