"""M1.32 local contour, unchanged-interface, load-connection and actual-gap checks."""
from common import *
from head_servo_detail import poses,yaw_pad_layout
from validate_head_cleanup import geometry_record


def validate_centered_pads(solids,check):
    s=P['head_servo_detail'];c=s['centered_yaw_pads'];m=s['mount'];h=P['head_print_cleanup']
    base=json.loads((PROJECT/c['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    retired=sorted(set(base['parts'])-set(now));old=base['Pitch_Yoke']
    old=manifold.Manifold(manifold.Mesh64(np.array(old['vertices_mm']),np.array(old['triangles'],dtype=np.uint64)))
    new=solids['Pitch_Yoke'].m;added=new-old;removed=old-new;layout=yaw_pad_layout()
    top=layout['seat_z_mm'];z0,z1=[D['head_z']+z for z in h['yoke_floor_z_from_head_mm']]
    def region(lo,hi):return manifold.Manifold.cube([b-a for a,b in zip(lo,hi)]).translate(lo)
    half=m['yaw_pad_width_x_mm']/2
    # Independent scope fence against M1.31, including the old outer front face.
    allowed=region([-half-.02,17.54,z0-.01],[half+.02,23.11,top+.01])
    allowed+=region([-half-.02,-17.51,z1-.01],[half+.02,-6.14,top+.01])
    outside=max(0,(added-allowed).volume())+max(0,(removed-allowed).volume())
    def ray(p0,p1):return [list(hit.position) for hit in new.ray_cast(p0,p1)]
    pads=[];errors=[];tol=c['hole_center_tolerance_mm']
    for i,y in enumerate(s['output_to_ear_hole_mm']):
        p=Vector((0,y,top-.05));distances=[]
        for d in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]:
            q=p+Vector(d)*15;hits=ray(list(p),list(q))
            distances.append((Vector(hits[-1])-p).length if len(hits)==2 else None)
        safe=region([-2.05,y-2.05,top-3.7],[2.05,y+2.05,top+.01])
        preserved_delta=max(0,(added^safe).volume())+max(0,(removed^safe).volume())
        zhits=ray([3,y,top-1],[3,y,top+1])
        top_error=abs(zhits[-1][2]-top) if zhits else 999
        radial_ok=all(d is not None for d in distances)
        center_error=max(abs(distances[0]-distances[1]),abs(distances[2]-distances[3]))/2 if radial_ok else 999
        row={'id':'Head_Yaw_Ear_'+str(i),'hole_center_mm':[0,y,top],
             'four_outer_edge_distances_mm':distances,'top_contour_center_error_mm':center_error,
             'ear_top_height_error_mm':top_error,'protected_bore_backing_difference_mm3':preserved_delta}
        pads.append(row)
        if center_error>tol or top_error>tol or preserved_delta>.005:errors.append(row)
    # Sample the beam away from the pad and rear web to measure both surfaces.
    beam_hits=ray([0,-12,top-8],[0,-12,top+1]);beam_z=sorted(v[2] for v in beam_hits)
    beam_thickness=beam_z[-1]-beam_z[0] if len(beam_z)==2 else None
    if beam_thickness is None or abs(beam_thickness-m['yaw_pad_thickness_mm'])>tol:errors.append({'beam_z':beam_z})
    # Both straight front-post side planes persist across two heights.
    post_profiles=[]
    for z in [z1+2,top-2]:
        hits=ray([4.5,16,z],[4.5,25,z]);edges=sorted(v[1] for v in hits)
        post_profiles.append({'z_mm':z,'edge_y_mm':edges})
        if len(edges)!=2 or max(abs(v-t) for v,t in zip(edges,layout['front_y_mm']))>tol:errors.append(post_profiles[-1])
    corner=region([-7.02,h['floor_depth_mm']/2+.001,z0-.01],[7.02,23.11,z1-.001])
    plain_post=region([-half,layout['front_y_mm'][0],z0],[half,layout['front_y_mm'][1],top])
    remaining=max(0,((new^corner)-plain_post).volume())
    gap=new.min_gap(solids['Yaw_Reaction_Link'].m,10)
    continuous=sum(v.volume()>.001 for v in new.decompose())==1
    ok=changed==['Pitch_Yoke'] and not retired and outside<.005 and not errors and remaining<.005 and continuous and gap>=c['minimum_reaction_clearance_mm']
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','baseline_revision':base['revision'],
        'changed_parts':changed,'retired_parts':retired,'part_count_delta':len(now)-len(base['parts']),
        'added_volume_mm3':max(0,added.volume()),'removed_volume_mm3':max(0,removed.volume()),
        'change_outside_declared_local_regions_mm3':outside,'pads':pads,'errors':errors,
        'unchanged_hole_pitch_mm':s['output_to_ear_hole_mm'][1]-s['output_to_ear_hole_mm'][0],
        'rear_arm_surface_z_mm':beam_z,'rear_arm_thickness_from_mesh_mm':beam_thickness,
        'rear_arm_drop_mm':c['rear_arm_drop_mm'],'reaction_link_actual_min_gap_mm':gap,
        'reaction_link_review_threshold_mm':c['minimum_reaction_clearance_mm'],
        'front_post_y_profiles':post_profiles,'corner_infill_remaining_mm3':remaining,
        'one_connected_solid':continuous,'sloped_support_added':False,
        'limits':['Actual triangle-solid checks and mesh rays; complete hardware and continuous motion are not certified.',
                  'Trial insert holes, print stiffness, fatigue, pullout and tolerances need physical verification.',
                  'Head routing remains deferred.']}
    save_json(ROOT/'reports/yaw_pad_centering_validation.json',result)
    check('head_servo_centered_pads',result['status'],'两处Yaw舵机座孔居中、原孔位不动、连接臂厚度与转轴间隙',result,
          'Per-part geometry/matrix comparison with M1.31; Manifold local difference volumes, actual mesh rays, connected components and triangle-solid min_gap.')
    corner_result={'revision':P['revision'],'status':'PASS' if remaining<.005 and continuous else 'FAIL',
        'baseline_revision':'V1.2-M1.30','scope':'M1.31 corner-cleanup invariant retained after authorized M1.32 pad-contour change',
        'superseded_full_shape_freeze':True,'corner_infill_remaining_mm3':remaining,'one_connected_solid':continuous,
        'sloped_support_added':False,'current_contour_validation':'yaw_pad_centering_validation.json',
        'limits':['Original full-post shape is intentionally superseded by centered M1.32 contour; original hole/servo datums retained. Physical strength NOT_TESTED.']}
    save_json(ROOT/'reports/head_seat_foot_validation.json',corner_result)
    check('head_servo_front_foot',corner_result['status'],'直角接角继续无残料；凸台外轮廓按M1.32授权收齐',corner_result,
          'Actual solid intersection in concave-corner region minus the current orthogonal post.')
