"""Independent visual hypotheses for photo-reconstructed CAM FPC connectors.

No hypothesis is adopted. Original board, optics and prints are unchanged.
The alternate view rotates only the selected reconstructed package triangles,
not any logical pin map or actual PCB footprint. It is not vendor CAD.
"""
from pathlib import Path
import json, sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex/connector_faces/orientation'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import bpy,COLS,P,D
from render import camera

ctx=Context(); scene=bpy.context.scene; tag='MORI_FFC_ORIENTATION_REVIEW__'
original=ctx.ss['CAM_Mainboard'].o
rows=json.loads(original['component_reference_index'])
rowmap={r['reference']:r for r in rows}
params={r['reference']:r for r in P['waveshare_detail']['cam']['parts']}
original_vertices=np.array([v.co[:] for v in original.data.vertices])
base=np.array(P['layout']['cam_board_center_from_head_mm'],float)
base[2]+=D['head_z']
assert np.allclose(np.array(original.matrix_world),np.eye(4))

items=[]; comparisons=[]
variants=[('current',[]),('camera_180',['CAMERA_FPC_24']),
          ('both_180',['CAMERA_FPC_24','DISPLAY_FPC_18'])]
for name, refs in variants:
    copy=original.copy();copy.data=original.data.copy();copy.name=tag+name
    scene.collection.objects.link(copy)
    copy['robot_part']=False;copy['category']='PURCHASED_REFERENCE'
    copy['data_status']='ASSUMED';copy['main_applied']=False
    copy['scope']='Photo orientation comparison only; no pinmap or physical mating claim.'
    v=original_vertices.copy();changed=np.zeros(len(v),dtype=bool);parts=[]
    for ref in refs:
        r=rowmap[ref];a,b=r['vertices'];u,w=params[ref]['center_uv_mm']
        center=base+np.array([u,0,w]);before=v[a:b].copy()
        v[a:b]=(v[a:b]-center)*np.array([-1,1,-1])+center
        changed[a:b]=True
        bounds_before=np.array([before.min(0),before.max(0)])
        bounds_after=np.array([v[a:b].min(0),v[a:b].max(0)])
        delta=float(np.max(np.abs(bounds_before-bounds_after)))
        assert delta<2e-5,(ref,delta)
        parts.append(dict(reference=ref,rotation_world_y_deg=180,
            pivot_mm=center.tolist(),vertex_range=[a,b],
            original_bounds_mm=bounds_before.tolist(),
            candidate_bounds_mm=bounds_after.tolist(),max_bounds_delta_mm=delta))
    for i,co in enumerate(v):copy.data.vertices[i].co=co
    copy.data.update()
    assert np.array_equal(v[~changed],original_vertices[~changed])
    comparisons.append(dict(variant=name,modified_components=parts,
        changed_component_vertex_count=int(changed.sum()),
        other_vertices_preserved=True,triangles_preserved=True,
        board_pose_unchanged=True,pinmap_modified=False))
    items.append(copy)

for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL'
scene.display.shading.light='STUDIO';scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True
scene.display.shading.background_type='WORLD';scene.world.color=(.9,.92,.94)
scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1200;scene.render.resolution_y=1200
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
images=[]
for obj,(name,refs) in zip(items,variants):
    for face,delta in [('SD',(0,-100,0)),('IC',(0,100,0))]:
        for o in items:o.hide_render=True
        obj.hide_render=False
        for n in ['Onboard_MIC_L','Onboard_MIC_R']:
            ctx.ss[n].o.hide_render=face!='SD'
        camera(tag+name+'_'+face,base+delta,base,44)
        path=OUT/(name+'_'+face+'.png')
        scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        images.append(dict(file=path.name,variant=name,face=face,
            camera_position_mm=(base+delta).tolist(),target_mm=base.tolist(),sha256=sha(path)))

for o in items:o.hide_render=True;o.hide_set(True)
items[0].hide_render=False;items[0].hide_set(False)
for n in ['Onboard_MIC_L','Onboard_MIC_R']:ctx.ss[n].o.hide_render=False
camera(tag+'saved_SD',base+(0,-100,0),base,44)
ctx.assert_unchanged()
blend=OUT/'MORI_M1_49_CAM_FPC_orientation_hypotheses.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
ctx.assert_unchanged()
sources={str((ROOT/'mechanical/scripts/waveshare_detail.py').relative_to(ROOT)):
    sha(ROOT/'mechanical/scripts/waveshare_detail.py')}
for name in ['esp32-s3-cam-ovxxxx-2_1.jpg','esp32-s3-cam-ovxxxx-3_1.jpg',
             'ESP32-S3-CAM-OVxxxx-details-5-2.jpg']:
    p=ROOT/'mechanical/sources/waveshare_detail'/name
    sources[str(p.relative_to(ROOT))]=sha(p)
result=dict(status='PASS',scope='Scoped unchanged-base extraction and visual hypotheses only',
    sources=ctx.sources,inputs=sources,comparisons=comparisons,images=images,
    blend=blend.name,blend_sha256=sha(blend),main_changed=False,
    adoption='NOT_APPLIED',actual_CAM_entry_directions='BLOCKED pending evidence reconciliation',
    exact_FPC_mating='BLOCKED',full_route='BLOCKED',
    limitations=['Rotating the simplified package is only a visualization hypothesis.',
        'Its fingers are illustrations, not a verified pin numbering or contact-face model.',
        'Unchanged AABB is not a collision or physical mating qualification.'],
    script_sha256=sha(Path(__file__)))
(OUT/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FFC_ORIENTATION_HYPOTHESES_DONE',flush=True)
