"""Verify a display-only repair against exact pre-change mechanical geometry."""
from common import *
from validate_head_cleanup import geometry_record
from head_surface_display import planar_faces


def normal_angle_deg(a,b):
    # Float64 atan2 avoids acos/float32 precision loss near parallel vectors.
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    a/=np.linalg.norm(a);b/=np.linalg.norm(b)
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b)))


def validate_head_surface(check):
    s=P.get('head_surface_display',{})
    if not s.get('enabled'):return
    before=json.loads((PROJECT/s['baseline_geometry']).read_text())['parts']
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=before.get(n));removed=sorted(set(before)-set(now))
    rows=[];failed=[]
    for name in s['target_part_ids']:
        o=bpy.data.objects[PREFIX+name];me=o.data;me.update();flat=planar_faces(o);normals=me.corner_normals
        deviations=[]
        for p,is_plane in zip(me.polygons,flat):
            if is_plane:
                angle=max(normal_angle_deg(p.normal,normals[k].vector) for k in p.loop_indices)
                deviations.append(angle)
                if p.use_smooth or angle>s['planar_alignment_tolerance_deg']:
                    failed.append({'id':name,'face':p.index,'corner_normal_error_deg':angle,'smooth':p.use_smooth})
        smooth=sum(p.use_smooth for p in me.polygons)
        if not smooth:failed.append({'id':name,'error':'All curved regions were flattened'})
        rows.append({'id':name,'checked_planar_faces':len(deviations),'maximum_planar_normal_error_deg':max(deviations,default=0),
                     'retained_smooth_curved_faces':smooth,'geometry_changed':name in changed})
    result={'revision':P['revision'],'baseline_revision':s['baseline_revision'],'status':'PASS' if not changed and not removed and not failed else 'FAIL',
            'geometry_changed':changed,'removed_parts':removed,'parts':rows,'normal_failures':failed,
            'method':'Exact rounded world/local vertex and triangle hashes and world matrices for every part; actual saved Blender corner normals versus geometric face normals, using float64 atan2 angles, for all designed planar faces; 0.05deg tolerance includes custom-normal storage quantization; curved faces retain smooth shading.',
            'effect':'Display normals only; physical wall, holes, motions and hardware datums preserved. Strength remains unqualified.'}
    check('head_surface_normals',result['status'],'头部平面消除假折皱；实际几何与上一版逐件一致',result)
    save_json(ROOT/'reports/head_surface_validation.json',result)
