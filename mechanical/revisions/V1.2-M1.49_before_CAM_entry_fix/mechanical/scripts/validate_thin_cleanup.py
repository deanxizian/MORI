"""M1.47 independent approved-shape/datum audit and historical delta adapter.

Historical checks undo only the approved signed volume difference. Their live
functional checks still use the current solids; this is not a collision waiver.
"""
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
import hashlib

_cache = None

def enabled():
    return P.get('prearrival_thin_cleanup',{}).get('enabled',False)

def declared_ids():
    return set(P['prearrival_thin_cleanup']['changed_existing_ids']) if enabled() else set()

def load_reference(path):
    # Blender appends same-named data without changing existing owned objects.
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        names=tuple(n for n in src.objects if n.startswith(PREFIX))
        dst.objects=list(names)
    loaded=[o for o in dst.objects if o]
    for o in loaded:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    result={}
    for original_name,o in zip(names,dst.objects):
        if o is None:continue
        if o.type!='MESH' or o.get('role')!='part' or o.get('group') in ['dock','coupon']:
            continue
        # Use requested names; Blender treats original numeric suffixes as IDs.
        name=original_name.removeprefix(PREFIX)
        s=Solid(o)
        result[name]={'record':geometry_record(o),'solid':s.m}
    for o in loaded:bpy.data.objects.remove(o,do_unlink=True)
    return result

def references():
    global _cache
    if _cache is None:
        q=P['prearrival_thin_cleanup']
        _cache=(load_reference(PROJECT/q['baseline_blend']),
                load_reference(PROJECT/q['approved_shape_source']))
    return _cache

def prior_solid(name, current):
    """Undo only M1.47's signed, immutable reviewed delta for older tests."""
    from validate_camera_cam import prior_solid as before_M1_48
    current=before_M1_48(name,current)
    if name not in declared_ids():return current
    before,approved=references();a=before[name]['solid'];b=approved[name]['solid']
    return (current-(b-a))+(a-b)

def validate_thin_cleanup(solids, check):
    if not enabled():return
    # Capture all real part fingerprints before reference import.
    now={n:geometry_record(s.o) for n,s in solids.items()}
    before,approved=references();ids=declared_ids()
    common=set(now)&set(before)
    changed=sorted(n for n in common if now[n]!=before[n]['record'])
    added=sorted(set(now)-set(before));retired=sorted(set(before)-set(now))
    rows=[]
    for n in sorted(ids):
        from neck_reference import prior_solid as before_M1_49
        a=before[n]['solid'];b=before_M1_49(n,solids[n].m);c=approved[n]['solid']
        rows.append(dict(id=n,added_mm3=max(0,(b-a).volume()),removed_mm3=max(0,(a-b).volume()),
                         candidate_difference_mm3=max(0,(b-c).volume())+max(0,(c-b).volume()),
                         connected_solids=len(solids[n].m.decompose()),historical_delta_components=len(b.decompose())))
    ok=(set(changed)==ids | declared_camera_cam_changes() | declared_neck_capacity_changes() and not added and not retired and
        all(r['candidate_difference_mm3']<.002 and r['connected_solids']==1 for r in rows))
    result=dict(status='PASS' if ok else 'FAIL',revision=P['revision'],
        source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        baseline_sha256=hashlib.sha256((PROJECT/P['prearrival_thin_cleanup']['baseline_blend']).read_bytes()).hexdigest(),
        approved_candidate_sha256=hashlib.sha256((PROJECT/P['prearrival_thin_cleanup']['approved_shape_source']).read_bytes()).hexdigest(),
        compared_parts=len(now),changed_ids=changed,new_ids=added,retired_ids=retired,solids=rows,
        reaction_link_unchanged='Yaw_Reaction_Link' not in changed,
        subsequent_approved_changes=sorted(declared_camera_cam_changes() | declared_neck_capacity_changes()),
        purchased_and_fastener_datums_unchanged=all(now[n]['world_matrix']==before[n]['record']['world_matrix'] for n in common if n not in ids),
        geometry_only=True,physical_strength='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/approved_thin_cleanup_validation.json',result)
    check('approved_thin_cleanup',result['status'],'M1.47三件匹配确认候选；后续相机/CAM五件变更另有专项核对',result)
    return result
