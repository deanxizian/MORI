"""Render the proved local negative-side return with its exact controls."""
from pathlib import Path
NV_SCRIPT=Path(__file__).resolve();NV_ROOT=NV_SCRIPT.parent
NV_HELPER=NV_ROOT/'render_CAM_contact_refined_forming.py';__file__=str(NV_HELPER)
exec(compile(NV_HELPER.read_text().split('\nscene=bpy.context.scene;',1)[0],str(NV_HELPER),'exec'),globals())
__file__=str(NV_SCRIPT)
NV_OUT=OR_OUT/'negative_return_branch';nv=json.loads((NV_OUT/'screen.json').read_text())
assert nv['status']=='PASS' and nv['complete_local_coverage']
or_path['stages'][3]['path']=nv['path']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=4
nv_images=[]
for label,f in [('side6',.8025),('side3',.825),('returned',.875)]:
    n,phases=or_pose(3,f);camera('A8_NEGATIVE_CAMERA',(-105,125,280),(-8,6,220),96)
    scene.render.filepath=str(NV_OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
    nv_images.append({'file':label+'.png','sha256':sha(NV_OUT/(label+'.png')),'fraction':f,
        'amplitude_mm':n['amplitude_mm'],'side_angle_deg':n['side_angle_deg'],'all_free_wire_phases':phases,
        'all_four_wires_and_contacts_present':True,'shown_structure_subset':sorted(show)})
assert all(geometry_record(o)==or_source[o.name] for o in parts() if o.name in or_source)
scene['independent_study']='Continuous nominal local return0.8025..0.875 only; other assembly and physical checks remain open.'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(NV_OUT/'review.blend'))
(NV_OUT/'render_manifest.json').write_text(json.dumps({'status':'PASS','script_sha256':sha(NV_SCRIPT),'helper_sha256':sha(NV_HELPER),
    'source_main_sha256':source_hash,'source_path_sha256':sha(NV_OUT/'screen.json'),'images':nv_images,
    'physical_source_objects_preserved':len(or_source),'review_sha256':sha(NV_OUT/'review.blend'),
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('NEGATIVE_RETURN_RENDER_DONE',len(nv_images),flush=True)
