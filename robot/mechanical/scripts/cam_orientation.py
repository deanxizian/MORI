"""Approved rigid CAM orientation, applied after the retained build phases.

The existing backplate, four seats, screws and acoustic holes stay unchanged.
No package is scaled or moved independently on the purchased PCB.
"""
from common import *

def transform():
    q=P.get('cam_orientation',{})
    if not q.get('enabled'):return np.eye(4)
    angle=q['rotation_about_world_Y_deg']
    assert angle==-90 and q['approved']
    # Exact quarter turn avoids introducing needless floating-point drift.
    r=np.array([[0.,0.,-1.],[0.,1.,0.],[1.,0.,0.]])
    c=np.array(P['layout']['cam_board_center_from_head_mm'],dtype=float);c[2]+=D['head_z']
    tr=np.eye(4);tr[:3,:3]=r;tr[:3,3]=c-r@c
    return tr

def apply_cam_orientation():
    q=P.get('cam_orientation',{})
    if not q.get('enabled'):return
    assembled();bpy.context.view_layer.update();tr=transform();r=tr[:3,:3];t=tr[:3,3]
    rows=[]
    for name in q['changed_existing_ids']:
        o=bpy.data.objects[PREFIX+name]
        assert not o.get('cam_orientation_revision'), 'Already rotated; rebuild from the original construction phases'
        for item in [o,bpy.data.objects[o['validation_proxy']]]:
            local=item.matrix_world.inverted()@Matrix(tr.tolist())@item.matrix_world
            item.data.transform(local);item.data.update();SOLIDS.pop(item.name,None)
        path=PROJECT/o['validation_solid_source'];cache=json.loads(path.read_text())
        vv=np.asarray(cache['vertices_mm'])@r.T+t;cache['vertices_mm']=vv.tolist()
        cache['cam_orientation_revision']=q['revision'];save_json(path,cache)
        refs=json.loads(o['component_reference_index'])
        visual=np.asarray([tuple(v) for v in vertices_world(o)])
        for row in refs:
            v=visual[slice(*row['vertices'])]
            row['bounds_xyz_mm']=[[float(v[:,i].min()),float(v[:,i].max())] for i in range(3)]
        o['component_reference_index']=json.dumps(refs,ensure_ascii=False)
        o['source_rotation']=(r@np.asarray(o['source_rotation'])).tolist()
        o['source_translation_mm']=(r@np.asarray(o['source_translation_mm'])+t).tolist()
        o['cam_orientation_revision']=q['revision']
        o['installed_orientation']='USB toward robot +X/right at head zero. L/R labels retain source channel identity, now lower/upper.'
        rows.append(dict(id=name,bounds_xyz_mm=bounds(o),components=refs))
    report=ROOT/'reports/waveshare_geometry.json';data=json.loads(report.read_text())
    data['CAM']['bounds_xyz_mm']=rows[0]['bounds_xyz_mm'];data['CAM']['components']=rows[0]['components']
    data['CAM']['installed_orientation']=q;save_json(report,data)
    save_json(ROOT/'reports/cam_orientation_geometry.json',dict(revision=P['revision'],
        config_source='config/geometry.json#/cam_orientation',transform_world_mm=tr.tolist(),
        parts=rows,USB_outward_world=[1,0,0],camera_FPC_outward_world=[-1,0,0],
        display_FPC_outward_world=[0,0,-1],new_parts=0,printed_changes=0,
        acoustic_performance='NOT_TESTED',full_harness='BLOCKED',manufacturing_release=False))
    print('CAM_USB_RIGHT_APPLIED',q['changed_existing_ids'],flush=True)
