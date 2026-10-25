"""Approved rear-shell DC trial seat; dimensions only from geometry.json.

The sample accessory meshes remain ASSUMED capacity references. They are not
manufacturer CAD and do not qualify the full cable passing through the hole.
"""
import hashlib
from common import *
from validate import Solid
from camera_cam_completion import replace_exact
from off_shelf_modules import parent_body


def transform(q):
    n=Vector(q['outward_normal'])
    origin=Vector(q['outer_surface_reference_mm'])-q['external_seat_recess_mm']*n
    return Matrix.Translation(origin)@n.to_track_quat('Z','Y').to_matrix().to_4x4()


def axial(q,r,z0,z1):
    m=manifold.Manifold.cylinder(z1-z0,r,r,q['segments'],False).translate([0,0,z0])
    return m.transform(np.asarray(transform(q),dtype=float)[:3,:])


def apply_dc_inlet_trial():
    q=P.get('dc_inlet_trial',{})
    if not q.get('enabled'):return
    assert q['approved']
    for source in q['sources'].values():
        assert hashlib.sha256((PROJECT/source['file']).read_bytes()).hexdigest()==source['sha256']
    assembled();bpy.context.view_layer.update()
    before=Solid(bpy.data.objects[PREFIX+'Body_Rear']).m
    add=axial(q,q['seat_diameter_mm']/2,-q['seat_wall_mm'],0)
    trim=axial(q,q['seat_diameter_mm']/2,*q['face_cut_z_mm'])
    bore=axial(q,q['trial_bore_mm']/2,*q['bore_cut_z_mm'])
    after=(before+add)-trim-bore
    assert after.status()==manifold.Error.NoError and len(after.decompose())==1
    # Float32 storage can collapse microscopic Boolean triangles. Simplify only
    # below the declared numerical threshold; saved geometry is compared to the
    # untouched approved mesh independently by validate_dc_inlet_trial.py.
    for _ in range(2):
        data=after.to_mesh64()
        after=manifold.Manifold(manifold.Mesh64(
            np.array(data.vert_properties[:,:3],dtype=np.float32).astype(float,order='C'),
            np.array(data.tri_verts,dtype=np.uint64,order='C'))).simplify(q['saved_float32_cleanup_mm'])
    assert after.status()==manifold.Error.NoError and len(after.decompose())==1
    shell=replace_exact('Body_Rear',after)
    shell['dc_inlet_trial_revision']=P['revision']
    shell['dc_inlet_status']='Approved sample-based diameter8 trial bore, integral 4mm seat; actual hole fit and complete lead insertion NOT_TESTED / BLOCKED'
    shell['dc_inlet_direction']='External flange / internal nut, from user-confirmed photos; no measured dimensions inferred'
    shell['material_suggestion']='PA12 structural prototype; physical strength and fit NOT_TESTED'
    tr=np.asarray(transform(q),dtype=float)[:3,:]
    references=[]
    for name,source_key in q['reference_ids'].items():
        source=q['sources'][source_key];cache=json.loads((PROJECT/source['file']).read_text())
        solids=[]
        for row in cache['solids']:
            m=manifold.Manifold(manifold.Mesh64(np.array(row['vertices'],dtype=float,order='C'),
                np.array(row['triangles'],dtype=np.uint64,order='C')))
            solids.append(m.translate(q['sample_to_local_translation_mm']))
        solid=manifold.Manifold.batch_boolean(solids,manifold.OpType.Add).transform(tr)
        data=solid.to_mesh64();o=mesh(name,data.vert_properties[:,:3].tolist(),data.tri_verts.tolist())
        o['preserve_vendor_tessellation']=True
        finish(o,'PLACEHOLDER','DC充电插座容量参考' if source_key=='jack_cache' else 'DC充电口螺母参考',
            'unknown','body',False,note=q['reference_limit'])
        o['data_status']='ASSUMED';o['model_fidelity']='SAMPLE_ALLOCATION_NOT_VENDOR_CAD'
        o['source_file']=source['file'];o['source_sha256']=source['sha256'];o['measured_unit']=False
        o['dc_inlet_trial_revision']=P['revision'];o['physical_fit']='NOT_TESTED'
        o['unknown_dimensions']='Exact thread, rigid tail, heatshrink and lead-end connector; sample dimensions retained without scaling'
        parent_body(o);references.append(name)
    bpy.context.scene['dc_trial_adoption']='USER_APPROVED; rear-shell trial seat and sample accessory references only'
    save_json(ROOT/'reports/dc_inlet_geometry.json',dict(revision=P['revision'],approved=True,
        construction_source='config/geometry.json#/dc_inlet_trial',changed_existing_ids=['Body_Rear'],
        new_reference_ids=references,new_prints=0,new_fasteners=0,integral_seat=True,
        frame='assembly mm; +Y forward, normal points rearward and upward',
        matrix_world=[list(r) for r in transform(q)],shell_connected_solids=len(after.decompose()),
        added_volume_mm3=float((after-before).volume()),removed_volume_mm3=float((before-after).volume()),
        actual_hole_fit='NOT_TESTED',complete_lead_insertion='BLOCKED',manufacturing_release=False))
    print('DC_TRIAL_APPLIED',references,flush=True)
