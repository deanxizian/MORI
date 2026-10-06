"""Review exact two-package correction scope against untouched M1.49 geometry."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex'; OUT=BASE/'connector_faces/correction'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,manifold,COLS,P,D,material
from native_electronics import COLORS
from cam_fpc_entry_geometry import corrected_component
from render import camera
from validate import rigidtr
ctx=Context();started=time.time();old=ctx.ss['CAM_Mainboard']; obj=old.o
source_vertices=np.asarray([obj.matrix_world@vertex.co for vertex in obj.data.vertices])
source_faces=np.asarray([list(poly.vertices) for poly in obj.data.polygons],dtype=np.int64)
rows=json.loads(obj['component_reference_index']); params={r['reference']:r for r in P['waveshare_detail']['cam']['parts']}
R=np.array([[1.,0,0],[0,0,-1.],[0,1.,0]])
center=np.asarray(P['layout']['cam_board_center_from_head_mm'],float);center[2]+=D['head_z']
v_all=[];f_all=[];mat_all=[];new_rows=[];changes=[];offset=0;face_offset=0;changed_solids={}
old_materials=list(obj.data.materials); old_mats=np.array([p.material_index for p in obj.data.polygons]); material_names=list(COLORS)
all_materials=old_materials+[material('MORI_fpc_correction_'+n,COLORS[n]) for n in material_names]
for row in rows:
    ref=row['reference']; a,b=row['vertices']; fa,fb=row['faces']; oldv=source_vertices[a:b]; oldf=source_faces[fa:fb]-a
    assert oldf.min()>=0 and oldf.max()<len(oldv)
    if ref not in ['CAMERA_FPC_24','DISPLAY_FPC_18']:
        vertices=oldv.copy();faces=oldf.copy();mats=old_mats[fa:fb].copy()
        assert np.array_equal(vertices,oldv) and np.array_equal(faces,oldf)
        result={k:v for k,v in row.items() if k not in ['vertices','faces']}
    else:
        result=corrected_component(params[ref],P['waveshare_detail']['cam']['pcb_thickness_mm'])
        vv=[];ff=[];mm=[];local=0;union=manifold.Manifold()
        for solid in result['solids']:
            vertices=np.asarray(solid['vertices_mm'])@R.T+center
            faces=np.asarray(solid['triangles'],dtype=np.uint64)
            vv.append(vertices);ff.append(faces+local);local+=len(vertices)
            mm.extend([len(old_materials)+material_names.index(solid['material'])]*len(faces))
            part=manifold.Manifold(manifold.Mesh64(vertices,faces));assert part.status()==manifold.Error.NoError;union+=part
        vertices=np.vstack(vv);faces=np.vstack(ff);mats=np.array(mm)
        bounds_before=np.array([oldv.min(0),oldv.max(0)]);bounds_after=np.array([vertices.min(0),vertices.max(0)])
        assert np.max(np.abs(bounds_before-bounds_after))<2e-5,(ref,bounds_before,bounds_after)
        original_part=manifold.Manifold(manifold.Mesh64(oldv,oldf.astype(np.uint64)))
        assert original_part.status()==manifold.Error.NoError
        changed_solids[ref]=dict(old=original_part,new=union)
        changes.append(dict(reference=ref,bounds_before_mm=bounds_before.tolist(),bounds_after_mm=bounds_after.tolist(),
            direction_uvw=result['entry_direction_uvw'],direction_world=(R@np.asarray(result['entry_direction_uvw'])).tolist(),
            old_volume_mm3=float(original_part.volume()),new_volume_mm3=float(union.volume()),
            added_volume_mm3=float((union-original_part).volume()),removed_volume_mm3=float((original_part-union).volume()),
            illustrative_mouth=result.get('illustrative_mouth'),limitations=result['limitations']))
        result={k:v for k,v in result.items() if k!='solids'}
    v_all.append(vertices);f_all.append(faces+offset);mat_all.extend(mats.tolist())
    result.update(vertices=[offset,offset+len(vertices)],faces=[face_offset,face_offset+len(faces)])
    new_rows.append(result);offset+=len(vertices);face_offset+=len(faces)
v=np.vstack(v_all);f=np.vstack(f_all)
scene=bpy.context.scene;tag='MORI_CAM_FPC_CORRECTED__';me=bpy.data.meshes.new(tag+'mesh')
me.from_pydata(v.tolist(),[],f.tolist());me.update()
new=bpy.data.objects.new(tag+'CAM_Mainboard',me);scene.collection.objects.link(new)
for mat in all_materials:me.materials.append(mat)
for poly,index in zip(me.polygons,mat_all):poly.material_index=index
new['robot_part']=False;new['category']='PURCHASED_REFERENCE';new['data_status']='ASSUMED'
new['component_reference_index']=json.dumps(new_rows,ensure_ascii=False);new['main_applied']=False
new['scope']='Only photo-established directions corrected; slot/contact dimensions remain illustrative.'
for row in new_rows:new.vertex_groups.new(name=row['reference']).add(list(range(*row['vertices'])),1.,'REPLACE')
np.savez_compressed(OUT/'CAM_Mainboard_candidate.npz',vertices_mm=v,triangles=f,material_indices=np.asarray(mat_all))
(OUT/'component_index.json').write_text(json.dumps(new_rows,ensure_ascii=False,indent=2)+'\n')

new_interferences=[];cases=[]
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        tr=np.asarray(rigidtr(yaw,pitch));ty=np.asarray(rigidtr(yaw,0));checked=0
        for ref,shapes in changed_solids.items():
            added=(shapes['new']-shapes['old']).transform(tr[:3,:]);points=np.asarray(added.to_mesh64().vert_properties[:,:3]);lo=points.min(0);hi=points.max(0)
            for name,s in ctx.ss.items():
                if name=='CAM_Mainboard':continue
                move=tr if s.group=='pitch' else ty if s.group=='yaw' else None
                tv=s.v if move is None else s.v@move[:3,:3].T+move[:3,3]
                if np.any(lo>tv.max(0)) or np.any(hi<tv.min(0)):continue
                target=s.m if move is None else s.m.transform(move[:3,:]);volume=float((added^target).volume());checked+=1
                if volume>1e-7:new_interferences.append(dict(yaw=yaw,pitch=pitch,reference=ref,part=name,new_overlap_mm3=volume))
        cases.append(dict(yaw=yaw,pitch=pitch,broadphase_candidates=checked))
    print('CAM_FPC_CORRECTION_POSE',yaw,'new_interferences',len(new_interferences),flush=True)
for col in COLS.values():col.hide_render=False;col.hide_viewport=False
for o in scene.objects:
    if o.type in ['MESH','CURVE','FONT']:o.hide_render=True;o.hide_set(True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=False;scene.display.shading.background_type='WORLD';scene.world.color=(.92,.94,.95)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1400;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';images=[]
for state,board in [('before',obj),('corrected',new)]:
    for o in [obj,new]:o.hide_render=True;o.hide_set(True)
    board.hide_render=False;board.hide_set(False)
    for side,eye in [('SD',center+[0,-100,0]),('IC',center+[0,100,0])]:
        camera(tag+state+side,eye,center,44);file=state+'_'+side+'.png';scene.render.filepath=str(OUT/file);bpy.ops.render.render(write_still=True)
        images.append(dict(file=file,sha256=sha(OUT/file)))
ctx.assert_unchanged()
blend=OUT/'MORI_M1_49_CAM_corrected_entries.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
report=dict(status='FAIL' if new_interferences else 'PASS',scope='Two-package photo-direction correction and added-volume checks; not a mated connector model',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [HERE/'cam_fpc_entry_geometry.py',ROOT/'mechanical/scripts/waveshare_detail.py',BASE/'connector_faces/direction_receipt.json']},
    changed_components=changes,unchanged_component_groups=len(rows)-2,unchanged_native_parts=len(ctx.ss),
    poses=130,pose_rows=cases,new_interferences=new_interferences,main_changed=False,adopted=False,
    exact_FPC_mating='BLOCKED',full_harness='BLOCKED',physical_validation='NOT_TESTED',
    blend=blend.name,blend_sha256=sha(blend),images=images,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_FPC_CORRECTION_DONE',report['status'],flush=True)
