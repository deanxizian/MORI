"""M1.56 approved central controller / side modules / direct UPS mount.

All construction parameters come from geometry.json. Independent approved
meshes are used by validation only. No electrical or native PCB file is edited.
"""
import hashlib
from common import *
from validate import Solid
from camera_cam_completion import replace_exact
from purchased_geometry import remove_generated
from native_electronics import aggregate


def cylinder(x, y, z0, z1, radius, segments=64):
    return manifold.Manifold.cylinder(z1-z0, radius, circular_segments=segments).translate([x,y,z0])


def hexagon(x, y, z0, z1, af):
    return cylinder(x,y,z0,z1,af/math.sqrt(3),6)


def construct(frame0, inserts, settings):
    """Rebuild the approved frame from the preceding construction phase."""
    q=settings; d=q['deck']; tr=np.array(q['controller_pose']['matrix_world']);frame=frame0
    seats=[];roots=[];fast={}
    for name,part in inserts.items():
        bb=np.array(part.bounding_box());x,y=(bb[:2]+bb[3:5])/2
        a,b=d['carrier_seat_capture_z_mm'];r=d['carrier_seat_capture_radius_mm']
        capture=cylinder(x,y,a,b,r,d['segments'])
        seats.append((frame0^capture).transform(tr[:3,:]))
        frame-=capture
        center=tr[:3,:3]@np.array([x,y,a])+tr[:3,3]
        roots.append(dict(id=name,xy_mm=center[:2].tolist()))
    for site in q['old_mount_sites']:
        x,y=site['xy'];a,b=d['old_top_cut_z_mm'] if site['side']=='top' else d['old_bottom_cut_z_mm']
        frame-=cylinder(x,y,a,b,site['r'],d['segments'])
        frame+=cylinder(x,y,d['bottom_z_mm'],d['top_z_mm'],d['pilot_fill_radius_mm'],d['segments'])
    for seat in seats:frame+=seat
    for s in q['small_board_mounts']:
        x,y=s['xy_mm'];i=s['index'];prefix='BMI323' if s['module']=='imu' else 'Buck6V'
        frame+=cylinder(x,y,d['small_seat_start_z_mm'],s['seat_top'],s['seat_r'])
        frame-=cylinder(x,y,d['small_hole_start_z_mm'],s['seat_top']+.1,s['pilot_r'])
        frame-=hexagon(x,y,d['small_hole_start_z_mm'],s['nut_z1'],s['pocket_af'])
        nut=hexagon(x,y,s['nut_z0'],s['nut_z1'],s['nut_af'])-cylinder(x,y,111.,113.,s['shank_r'])
        z=s['head_bottom'];tip=z-s['length']
        screw=cylinder(x,y,tip,z+.01,s['shank_r'])+cylinder(x,y,z,z+s['head_h'],s['head_d']/2)
        screw-=hexagon(x,y,z+s['head_h']-s['socket_depth'],z+s['head_h']+.1,s['key_af'])
        fast[f'{prefix}_Screw_{i}']=screw;fast[f'{prefix}_Nut_{i}']=nut
    # The approved direct-seat phase used the saved center layout as its input.
    # Quantize at that boundary, matching Blender's vertex precision explicitly.
    a=frame.to_mesh64()
    frame=manifold.Manifold(manifold.Mesh64(np.array(a.vert_properties[:,:3],dtype=np.float32).astype(float,order='C'),
                                           np.array(a.tri_verts,dtype=np.uint64,order='C')))
    assert frame.status()==manifold.Error.NoError
    u=q['ups_mount'];segments=u['segments']
    for i,(x,y) in enumerate(u['centers_xy_mm']):
        c=lambda zz,r:cylinder(x,y,*zz,r,segments)
        frame+=c(u['seat_z_mm'],u['seat_radius_mm'])
        frame-=c(u['through_bore_z_mm'],u['through_bore_radius_mm'])
        screw=c(u['screw_shank_z_mm'],u['screw_radius_mm'])+c(u['screw_head_z_mm'],u['screw_head_radius_mm'])
        screw-=hexagon(x,y,*u['hex_socket_z_mm'],u['hex_socket_af_mm'])
        nut=hexagon(x,y,*u['nut_z_mm'],u['nut_af_mm'])-c(u['nut_bore_z_mm'],u['screw_radius_mm'])
        fast[f'UPS_Direct_Screw_{i}']=screw;fast[f'UPS_Direct_Nut_{i}']=nut
    assert frame.status()==manifold.Error.NoError and len(frame.decompose())==1
    # Remove sub-micron Boolean tessellation remnants before float32 storage;
    # independent adoption comparison limits any surface/volume change.
    for _ in range(2):
        a=frame.to_mesh64()
        frame=manifold.Manifold(manifold.Mesh64(np.array(a.vert_properties[:,:3],dtype=np.float32).astype(float,order='C'),
                                               np.array(a.tri_verts,dtype=np.uint64,order='C'))).simplify(d['saved_float32_cleanup_mm'])
    return frame,fast,roots


def parent_body(o):
    world=o.matrix_world.copy();o.parent=bpy.data.objects[PREFIX+'CTRL_Root'];o.matrix_world=world
    o['assembled_local_location_mm']=list(o.location)


def move_controller(names, transform):
    """Move visible objects AND exact world-coordinate validation sources."""
    tr=np.asarray(transform);moved=set()
    for n in names:
        o=bpy.data.objects[PREFIX+n]
        for target in [o]+([bpy.data.objects[o['validation_proxy']]] if o.get('validation_proxy') else []):
            if target.name in moved:continue
            target.matrix_world=Matrix(transform)@target.matrix_world
            target['assembled_local_location_mm']=list(target.location);moved.add(target.name)
            SOLIDS.pop(target.name,None)
        if o.get('validation_solid_source'):
            data=json.loads((PROJECT/o['validation_solid_source']).read_text())
            data['vertices_mm']=(np.array(data['vertices_mm'])@tr[:3,:3].T+tr[:3,3]).tolist()
            path=ROOT/'reports'/f'solid_{n}_M1_56.json';save_json(path,data)
            o['validation_solid_source']=str(path.relative_to(PROJECT))
        for rk,tk in [('source_rotation','source_translation_mm'),
                      ('source_transform_rotation','source_transform_translation_mm')]:
            if rk in o and tk in o:
                o[rk]=(tr[:3,:3]@np.asarray(o[rk])).tolist()
                o[tk]=(tr[:3,:3]@np.asarray(o[tk])+tr[:3,3]).tolist()
        if o.get('component_reference_index'):
            rows=json.loads(o['component_reference_index'])
            for row in rows:
                bb=row['bounds_xyz_mm'];corners=np.array([[x,y,z] for x in bb[0] for y in bb[1] for z in bb[2]])
                vv=corners@tr[:3,:3].T+tr[:3,3]
                row['bounds_xyz_mm']=np.stack((vv.min(0),vv.max(0)),axis=1).tolist()
            o['component_reference_index']=json.dumps(rows,ensure_ascii=False)
        o['off_shelf_revision']=P['revision']
        o['placement_status']='Approved rigid relocation; received P5R7 electrical design and E header interface remain provisional'
    bpy.context.view_layer.update()


def add_module(key, settings):
    q=settings;spec=q['modules'][key];source=q['sources']
    for field in [key+'_step',key+'_cache']+(['imu_socket'] if key=='imu' else []):
        row=source[field];assert hashlib.sha256((PROJECT/row['file']).read_bytes()).hexdigest()==row['sha256']
    cache=json.loads((PROJECT/source[key+'_cache']['file']).read_text())
    assert cache['source_sha256']==source[key+'_step']['sha256'] and cache['units']=='mm' and cache['scale_factor']==1
    components=[]
    for row in cache['solids']:
        if row['index'] in spec['omit_solid_indices']:continue
        color='pcb' if (key=='buck' and row['index']==0) or (key=='imu' and row['index']==69) else 'dark'
        components.append(dict(reference=f'CAD_{row["index"]:03}',value=spec['sku'],evidence=spec['data_status'],
            dimension_basis='Unscaled original vendor source tessellation',limitations=spec['limit'],
            solids=[dict(vertices_mm=row['vertices'],triangles=row['triangles'],material=color)]))
    if key=='imu':
        row=json.loads((PROJECT/source['imu_socket']['file']).read_text())
        components.append(dict(reference='SOCKET_OPEN_SURFACE',value='Original board socket housing',evidence='VENDOR_DOCUMENTED',
            dimension_basis='Original free shell, not a fabricated closed solid',limitations='Original open surface; conservative AABB in collision checks',
            solids=[dict(vertices_mm=row['vertices'],triangles=row['triangles'],material='ivory')]))
    tr=np.asarray(spec['matrix_world'])
    obj,solid,rows,fallbacks=aggregate(spec['id'],dict(components=components,source_revision='Official file receipt 2026-10-13',limit=spec['limit']),
        tr[:3,:3],tr[:3,3],spec['label'])
    obj['category']=spec['category'];obj['data_status']=spec['data_status'];move_collection(obj,spec['category'])
    obj['interface_status']=spec['limit'];obj['model_fidelity']='VENDOR_FAMILY_CAD_ASSUMED_MATCH' if key=='buck' else 'VENDOR_SIMPLIFIED_CAD' if key=='ups' else 'VENDOR_CAD_WITH_OPEN_SOCKET'
    obj['source_file']=source[key+'_step']['file'];obj['source_sha256']=source[key+'_step']['sha256']
    obj['source_mesh_file']=source[key+'_cache']['file'];obj['source_mesh_sha256']=source[key+'_cache']['sha256']
    obj['selected_sku']=spec['sku'];obj['manufacturer']=spec['manufacturer'];obj['physical_fit']='NOT_TESTED';obj['off_shelf_revision']=P['revision']
    if key=='buck':
        obj.data.materials.clear();obj.data.materials.append(MATS['unknown'])
        for f in obj.data.polygons:f.material_index=0
    if key=='ups':
        obj.data.materials.clear();obj.data.materials.append(material('UPS_source_simplification',(.13,.42,.52)))
        for f in obj.data.polygons:f.material_index=0
    parent_body(obj);parent_body(bpy.data.objects[obj['validation_proxy']])
    return dict(id=spec['id'],source_solid_count=len(cache['solids'])-len(spec['omit_solid_indices']),
                display_components=len(rows),fallbacks=fallbacks,source_scale_factor=1.,matrix_world=spec['matrix_world'])


def apply_off_shelf_modules():
    q=P.get('off_shelf_modules',{})
    if not q.get('enabled'):return
    assert q['approved']
    assembled();bpy.context.view_layer.update()
    frame0=Solid(bpy.data.objects[PREFIX+'Load_Frame']).m
    inserts={n:Solid(bpy.data.objects[PREFIX+n]).m for n in q['controller_group_ids'] if n.startswith('Carrier_Insert_')}
    frame,fast,roots=construct(frame0,inserts,q)
    o=replace_exact('Load_Frame',frame);o['off_shelf_revision']=P['revision']
    o['interface_status']='UPS direct four M3 through-bolt seats, centered controller and two side modules; approved trial PA12 geometry, strength not qualified'
    o['material_suggestion']='PA12; first structural prototype, physical fit and strength NOT_TESTED'
    o['functional_purpose']='Shared deck and direct UPS support; no separate battery tray'
    move_controller(q['controller_group_ids'],q['controller_pose']['matrix_world'])
    for n in q['retired_ids']:
        old=bpy.data.objects.get(PREFIX+n)
        if old and old.get('validation_proxy'):remove_generated(old['validation_proxy'].removeprefix(PREFIX))
        remove_generated(n)
    modules=[add_module(k,q) for k in ('ups','imu','buck')]
    for name,m in fast.items():
        a=m.to_mesh64();o=mesh(name,a.vert_properties[:,:3].tolist(),a.tri_verts.tolist())
        o['preserve_vendor_tessellation']=True
        size='M3×25 / M3' if name.startswith('UPS_') else 'M1.6×8 / M1.6' if name.startswith('BMI323') else 'M2×10 / M2'
        finish(o,'PLACEHOLDER',size+(' 螺母' if '_Nut_' in name else ' 内六角螺钉'),'unknown','body',False,
               note='Standard catalogue nominal envelope; supplier not selected, thread helix and physical tolerances NOT_TESTED')
        o['data_status']='ASSUMED';o['model_fidelity']='STANDARD_FASTENER_NOMINAL_ENVELOPE';o['off_shelf_revision']=P['revision']
        o['functional_purpose']='常规金属紧固件，非打印件';parent_body(o)
    for n in ['Rear_Interface_PCB','USB_Receptacle']:
        o=bpy.data.objects.get(PREFIX+n)
        if o:o['current_route_status']='Historical P5R7 physical reference retained; rear DC/5V/power-cut electrical and shell interface redesign BLOCKED'
    scene=bpy.context.scene;scene['revision']=P['revision'];scene['off_shelf_adoption']='USER_APPROVED, direct UPS mount, central F412, BMI323 and 6V-family Buck'
    scene['full_harness']='NOT_TESTED: prior body routes invalidated by changed architecture';scene['manufacturing_release']=False
    save_json(ROOT/'reports/off_shelf_geometry.json',dict(revision=P['revision'],approved=True,
        construction_source='config/geometry.json#/off_shelf_modules',changed_prints=['Load_Frame'],
        transformed_ids=q['controller_group_ids'],retired_ids=q['retired_ids'],new_ids=[r['id'] for r in modules]+list(fast),
        modules=modules,controller_roots=roots,frame_components=len(frame.decompose()),
        frame_added_mm3=float((frame-frame0).volume()),frame_removed_mm3=float((frame0-frame).volume()),
        physical_strength='NOT_TESTED',full_harness='NOT_TESTED',electrical_adaptation='BLOCKED',manufacturing_release=False))
    print('OFF_SHELF_M1_56_APPLIED',len(fast),len(modules),flush=True)
