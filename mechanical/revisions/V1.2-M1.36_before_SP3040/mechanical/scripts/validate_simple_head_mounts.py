"""M1.34: paired printed bores, unchanged lug outlines and exact flat-seat return."""
from common import *
from validate_head_cleanup import geometry_record
from head_servo_detail import yaw_pad_layout


def validate_simple_head_mounts(solids,Solid,iv,check):
    s=P.get('head_mount_simplification',{})
    if not s.get('enabled'):return
    base=json.loads((PROJECT/s['baseline_geometry']).read_text())
    flat=json.loads((PROJECT/s['flat_yoke_reference']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    retired=sorted(set(base['parts'])-set(now))
    def solid(row):
        return manifold.Manifold(manifold.Mesh64(np.array(row['vertices_mm']),np.array(row['triangles'],dtype=np.uint64)))
    def vol(m):return max(0.,m.volume())
    def cylinder(x,y,z0,z1,r):
        return manifold.Manifold.cylinder(z1-z0,r,circular_segments=P['mesh']['cylinder_segments']).translate([x,y,z0])
    def distance_ray(m,p,d,length=15):
        a=Vector(p);hits=m.ray_cast(list(a),list(a+Vector(d)*length))
        return [float((Vector(h.position)-a).length) for h in hits]
    tolerance=s['numeric_tolerance_mm'];volume_tolerance=s['local_volume_tolerance_mm3']
    h=P['head_print_cleanup'];hz=D['head_z'];z1=hz+h['cradle_top_from_head_mm'];top=hz+h['cradle_shell_lug_top_from_head_mm']
    completion=P.get('assembly_completion',{});later=set()
    if completion.get('enabled'):later.update(completion['changed_existing_ids']+completion['new_ids'])
    later.update(declared_cap_edge_changes())
    rows=[];errors=[];local=[]
    for name,radius,low,high in [('Pitch_Cradle',1.2,z1-2,top+2),('Head_Front',1.6,hz+24.5,hz+31.7)]:
        old=solid(base[name]);new=solids[name].m;added=new-old;removed=old-new
        region=manifold.Manifold()
        for sign in [-1,1]:
            x,y=head_shell_mount_xy_mm(sign)
            # A little numerical allowance, never a broad box authorizing an outline edit.
            region+=cylinder(sign*48,3,low-.01,high+.01,radius+.01)
            region+=cylinder(x,y,low-.01,high+.01,radius+.01)
        if completion.get('enabled'):
            # Preserve this earlier check on its exact lug area; other M1.35
            # edits are independently bounded by completion_scope.
            protected=manifold.Manifold()
            for sign in [-1,1]:
                protected+=manifold.Manifold.cube([13,9,25],True).translate([sign*47.5,3.5,246])
            added=added^protected;removed=removed^protected
        outside=vol(added-region)+vol(removed-region)
        one=sum(m.volume()>.001 for m in new.decompose())==1
        whole_bounds_error=float(np.max(np.abs(np.array(new.bounding_box())-np.array(old.bounding_box()))))
        bb=np.array((new^protected).bounding_box() if completion.get('enabled') else new.bounding_box());oldbb=np.array((old^protected).bounding_box() if completion.get('enabled') else old.bounding_box())
        row={'part':name,'added_mm3':vol(added),'removed_mm3':vol(removed),
             'change_outside_old_and_new_bores_mm3':outside,'bounds_error_mm':float(np.max(np.abs(bb-oldbb))),
             'one_connected_solid':one,'whole_bounds_change_mm':whole_bounds_error,'scope':'Paired shell-lug regions only; M1.35 rear PCB wall and camera lips checked separately' if completion.get('enabled') else 'Whole original part'}
        local.append(row)
        if outside>volume_tolerance or row['bounds_error_mm']>tolerance or not one:errors.append(row)
    for sign in [-1,1]:
        x,y=head_shell_mount_xy_mm(sign);z=top-.1;dims=[];bores=[]
        for name,radius,testz in [('Pitch_Cradle',1.2,z),('Head_Front',1.6,hz+28.1)]:
            samples=[distance_ray(solids[name].m,(x,y,testz),d) for d in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]]
            bores.append({'part':name,'center_mm':[x,y,testz],'radial_surface_distances_mm':samples})
            if any(not a or abs(a[0]-radius)>tolerance for a in samples):errors.append(bores[-1])
            if name=='Pitch_Cradle':dims=[a[1] if len(a)==2 else None for a in samples]
        error=max(abs(dims[0]-dims[1]),abs(dims[2]-dims[3]))/2 if all(a is not None for a in dims) else 999
        # The axis remains open across the cradle/shell mating plane.
        axis=[{'part':name,'hits':[list(a.position) for a in solids[name].m.ray_cast([x,y,z1+.1],[x,y,top+1])]} for name in ['Pitch_Cradle','Head_Front']]
        cap=sorted(a.position[2] for a in solids['Head_Front'].m.ray_cast([x,y,hz+31.5],[x,y,hz+34]))
        material=[]
        for name,zlo,zhi in [('Pitch_Cradle',top-.8,top-.2),('Head_Front',top+.2,top+.8)]:
            annulus=cylinder(x,y,zlo,zhi,2.5)-cylinder(x,y,zlo-.01,zhi+.01,1.7)
            missing=vol(annulus-solids[name].m);material.append({'part':name,'missing_annular_material_mm3':missing})
            if missing>volume_tolerance:errors.append(material[-1])
        row={'side':sign,'paired_xy_mm':[x,y],'old_xy_mm':[sign*48,3],
             'unchanged_lug_top_size_xy_mm':[h['cradle_shell_lug_outer_x_mm']-h['cradle_outer_half_width_mm']+h['cradle_wall_mm'],h['cradle_shell_lug_depth_mm']],
             'four_top_edge_distances_mm':dims,'bore_to_top_center_error_mm':error,'bores':bores,
             'axis_through_mating_plane':axis,'axial_blind_cap_surfaces_mm':cap,
             'sampled_lug_min_side_material_mm':min(dims)-1.2 if all(a is not None for a in dims) else None,
             'material_probes':material}
        rows.append(row)
        # The first two surfaces bound the lug's blind cap. A third surface
        # farther above is the separate curved shell wall, not a cap defect.
        if error>tolerance or any(v['hits'] for v in axis) or len(cap)<2 or cap[1]-cap[0]<1.2:errors.append(row)
    original=solid(flat['Pitch_Yoke']);yoke=solids['Pitch_Yoke'].m
    difference=vol(yoke-original)+vol(original-yoke)
    layout=yaw_pad_layout();seat=layout['seat_z_mm'];plane=[]
    # Sample the unsupported arm span; y=-16 passes through its vertical web.
    for y in [-14,-12,-8]:
        hits=sorted(a.position[2] for a in yoke.ray_cast([4,y,seat-6],[4,y,seat+1]))
        plane.append({'x_mm':4,'y_mm':y,'surface_z_mm':hits})
        if len(hits)!=2 or abs(hits[-1]-seat)>tolerance or abs(hits[-1]-hits[0]-P['head_servo_detail']['mount']['yaw_pad_thickness_mm'])>tolerance:errors.append(plane[-1])
    restoration={'reference_revision':flat['revision'],'solid_symmetric_difference_mm3':difference,
                 'same_mesh_and_matrix_as_reference':now['Pitch_Yoke']==flat['parts']['Pitch_Yoke'],
                 'flat_rear_pad_surface_samples':plane,'rear_step_mm':seat-layout['rear_arm_top_z_mm'],
                 'reaction_link_actual_gap_mm':yoke.min_gap(solids['Yaw_Reaction_Link'].m,10)}
    if difference>volume_tolerance or restoration['rear_step_mm']!=0:errors.append(restoration)
    ok=not (set(changed)-set(s['changed_existing_ids'])-later) and not retired and not errors
    r={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','baseline_revision':base['revision'],
       'changed_parts':changed,'unexpected_changes':sorted(set(changed)-set(s['changed_existing_ids'])-later),
       'retired_parts':retired,'new_parts':sorted(set(now)-set(base['parts'])),
       'holes':rows,'local_scope':local,'yaw_flat_restoration':restoration,'errors':errors,
       'limits':['Nominal triangle-solid bores and sampled material; no complete minimum-wall or stress calculation.',
                 'Trial shell fastening/inserts still need matching fasteners, access review, coupons and physical assembly.',
                 'Existing camera conflicts and deferred wiring are not resolved by this change.']}
    save_json(ROOT/'reports/simple_head_mounts_validation.json',r)
    check('simple_head_mounts',r['status'],'撤回误改的舵机座台阶；头壳固定孔配对居中，凸台外形和硬件保持',r,
          'All-part mesh/matrix comparison vsM1.33; actual-solid delta restricted to old/new bore cylinders; paired-axis rays, edge/material probes and yoke solid comparison withM1.31.')
