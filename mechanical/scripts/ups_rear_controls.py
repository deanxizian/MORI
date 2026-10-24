"""Approved upper DC/lower switch arrangement; geometry.json is the sole source.

Retained sample meshes are ASSUMED capacity references. No video or PCB edits.
"""
import hashlib
from common import *
from validate import Solid
from camera_cam_completion import replace_exact
from monocoque_structure import source_build
from off_shelf_modules import parent_body
from dc_inlet_trial import transform, axial


def boxm(lo,hi):
    return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)


def apply_ups_rear_controls():
    q=P.get('ups_rear_controls',{})
    if not q.get('enabled'):return
    assert q['approved']
    for r in q['sources'].values():
        assert hashlib.sha256((PROJECT/r['file']).read_bytes()).hexdigest()==r['sha256'],r['file']
    assembled();bpy.context.view_layer.update()
    before=Solid(bpy.data.objects[PREFIX+'Body_Rear']).m
    b=source_build();o=b.body_outer('controls_mother');outer=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
    o=b.body_outer('controls_inner',P['shell_thickness_mm']);inner=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
    usb=boxm(*q['legacy_usb_fill_bounds_mm']);ledges=manifold.Manifold()
    for bounds in q['retired_ledge_bounds_mm']:ledges+=boxm(*bounds)
    base=(before+((outer-inner)^usb))-(inner^ledges)
    s=q['switch'];seat=axial(s,s['seat_diameter_mm']/2,-s['seat_wall_mm'],0)
    face=axial(s,s['seat_diameter_mm']/2,*s['face_cut_z_mm']);bore=axial(s,s['trial_bore_mm']/2,*s['bore_cut_z_mm'])
    after=(base+seat)-face-bore
    for _ in range(2):
        d=after.to_mesh64()
        after=manifold.Manifold(manifold.Mesh64(np.array(d.vert_properties[:,:3],dtype=np.float32).astype(float,order='C'),np.array(d.tri_verts,dtype=np.uint64,order='C'))).simplify(q['saved_float32_cleanup_mm'])
    assert after.status()==manifold.Error.NoError and len(after.decompose())==1
    for n in q['retired_ids']:
        o=bpy.data.objects[PREFIX+n];assert o.get('mori_owner')==OWNER
        if o.get('validation_proxy'):
            proxy=bpy.data.objects.get(o['validation_proxy'])
            if proxy:bpy.data.objects.remove(proxy,do_unlink=True)
        SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
    shell=replace_exact('Body_Rear',after)
    shell['ups_controls_revision']=P['revision'];shell['ups_controls_status']='USER_APPROVED upper DC/lower switch; trial seats, actual fit NOT_TESTED'
    shell['material_suggestion']='PA12 structural prototype; strength NOT_TESTED'
    tr=np.asarray(transform(s),dtype=float)[:3,:]
    for n,k in q['reference_ids'].items():
        source=q['sources'][k];cache=json.loads((PROJECT/source['file']).read_text())
        assert cache['units']=='mm' and cache['scale_factor']==1
        solids=[]
        for row in cache['solids']:
            m=manifold.Manifold(manifold.Mesh64(np.array(row['vertices'],dtype=float,order='C'),np.array(row['triangles'],dtype=np.uint64,order='C')))
            solids.append(m.translate(s['sample_to_local_translation_mm']))
        m=manifold.Manifold.batch_boolean(solids,manifold.OpType.Add).transform(tr);d=m.to_mesh64()
        o=mesh(n,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist())
        finish(o,'PLACEHOLDER','UPS原配开关容量参考' if k=='switch_cache' else 'UPS开关螺母参考','unknown','body',False,note=q['reference_limit'])
        o['data_status']='ASSUMED';o['model_fidelity']='SAMPLE_ALLOCATION_NOT_VENDOR_CAD';o['source_scale_factor']=1.
        o['source_file']=source['file'];o['source_sha256']=source['sha256'];o['physical_fit']='NOT_TESTED';o['ups_controls_revision']=P['revision']
        parent_body(o)
    bpy.context.scene['ups_rear_controls']='USER_APPROVED upper DC/lower switch; retired rear interface PCB'
    carrier=bpy.data.objects[PREFIX+'MCU_Carrier']
    carrier['electrical_adaptation_status']='P5R7 native geometry retained as capacity reference; UPS-R1 new carrier connectors/protection not frozen'
    save_json(ROOT/'reports/ups_controls_geometry.json',dict(revision=P['revision'],approved=True,construction_source='config/geometry.json#/ups_rear_controls',changed_existing_ids=['Body_Rear'],retired_ids=q['retired_ids'],new_reference_ids=list(q['reference_ids']),switch_matrix_world=[list(r) for r in transform(s)],new_prints=0,retired_screws=2,retired_inserts=2,shell_connected_solids=len(after.decompose()),added_volume_mm3=float((after-before).volume()),removed_volume_mm3=float((before-after).volume()),physical_fit='NOT_TESTED',complete_lead_insertion='BLOCKED',manufacturing_release=False))
    print('UPS_REAR_CONTROLS_APPLIED',q['retired_ids'],flush=True)
