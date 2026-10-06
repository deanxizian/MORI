"""Independent J1 route/solid candidate. Never modifies the main blend/config."""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT)
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record
OUT=SCRIPT.parent/'joined_entry_candidate';OUT.mkdir(exist_ok=True)
path=SCRIPT.parent/'joined_entry_screen.json';route=json.loads(path.read_text())
assert route['source_blend_sha256']==before
assert route['source_obstacle_ids']==['Pitch_Yoke','Yaw_Base']
assert not route['fixed_wire_hits']
baseline={name:geometry_record(s.o) for name,s in ss.items()}
original={n:s.m for n,s in ss.items()}
cut_radius=.78
changed_parts=['Yaw_Base','Pitch_Yoke'];cuts={};results={}
for target in changed_parts:
    tubes=[];s=ss[target];seen=set()
    for row in route['rows']:
        pts=np.asarray(row['curve_mm'])
        if s.group=='yaw':
            inv=np.linalg.inv(np.asarray(rigidtr(row['yaw_deg'],0)))
            pts=pts@inv[:3,:3].T+inv[:3,3]
        # Short chords with rounded joins. Keep segments wholly inside a solid,
        # too: distance-to-surface alone cannot reject an interior segment.
        # Duplicates are eliminated geometrically.
        pts=np.vstack([pts[::3],pts[-1]])
        for a,b in zip(pts,pts[1:]):
            ln=float(np.linalg.norm(b-a))
            if ln<1e-9:continue
            if np.any(np.maximum(a,b)<s.lo-cut_radius) or np.any(np.minimum(a,b)>s.hi+cut_radius):continue
            key=tuple(np.round(np.r_[a,b],4))
            if key in seen:continue
            seen.add(key)
            tubes.extend([axial(cut_radius,ln,(a+b)/2,(b-a)/ln,segments=48),
                          manifold.Manifold.sphere(cut_radius,32).translate(a.tolist()),
                          manifold.Manifold.sphere(cut_radius,32).translate(b.tolist())])
    cut=manifold.Manifold.batch_boolean(tubes,manifold.OpType.Add)
    new=s.m-cut
    assert new.status()==manifold.Error.NoError
    removed=s.m-new;cuts[target]=removed
    components=[float(m.volume()) for m in new.decompose()]
    replace_owned(target,new)
    ss[target]=Solid(s.o);trees[target]=ss[target].bvh()
    for suffix,m in [('baseline',original[target]),('candidate',new),('removed',removed)]:
        mesh=m.to_mesh64()
        np.savez_compressed(OUT/f'{target}_{suffix}.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),
                            triangles=np.asarray(mesh.tri_verts))
    gaps=[]
    for name,t in ss.items():
        if name==target or name in changed_parts:continue
        bb=np.asarray(removed.bounding_box());dist=np.maximum(np.maximum(bb[:3]-t.hi,t.lo-bb[3:]),0)
        if np.linalg.norm(dist)>5:continue
        gaps.append(dict(part=name,removed_to_part_gap_mm=float(removed.min_gap(t.m,5))))
    results[target]=dict(removed_volume_mm3=float(removed.volume()),remaining_components_mm3=components,
                         near_source_parts=gaps)
    print('JOINED_CANDIDATE_CUT',target,len(seen),round(removed.volume(),6),components,flush=True)

# Check the complete joined line again. A single body/yaw frame test per yaw
# represents all pitches for those source groups; pitch parts use all 10 poses.
hits=[];fixed_hits=[]
for row in route['rows']:
    pts=np.asarray(row['curve_mm']);yaw=row['yaw_deg'];angle=row['azimuth_deg'];err=row['error_bound_mm']
    for name,s in ss.items():
        for pitch in (range(-20,26,5) if s.group=='pitch' else [0]):
            if s.group in ['yaw','pitch']:
                inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                local=pts@inv[:3,:3].T+inv[:3,3]
            else:local=pts
            h=sample_clear(local,.3302,err,[name])
            if h:hits.append(dict(yaw_deg=yaw,pitch_deg=pitch,azimuth_deg=angle,**h));break
    h=fixed_clear(pts,.3302,err)
    if h:fixed_hits.append(dict(yaw_deg=yaw,azimuth_deg=angle,**h))
changed=sorted(n for n,s in ss.items() if baseline[n]!=geometry_record(s.o))
assert changed==sorted(changed_parts),changed

sections={}
for angle in [0,45,90,135]:
    a=math.radians(angle)
    tr=np.array([[0,0,1,0],[math.cos(a),math.sin(a),0,0],[-math.sin(a),math.cos(a),0,0]])
    layers={n:ss[n].m for n in ['Yaw_Base','Pitch_Yoke','Yaw_Reaction_Link','Yaw_Bearing','Yaw_Servo','Pitch_Servo']}
    layers.update({n+'_baseline':original[n] for n in changed_parts})
    layers.update({n+'_removed':cuts[n] for n in changed_parts})
    sections[str(angle)]={n:[np.asarray(p)[:,[1,0]].tolist() for p in m.transform(tr).slice(0).to_polygons()]
                          for n,m in layers.items()}
(OUT/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')

bpy.context.scene['independent_unapproved_study']='A8 J1: connected UART staging curves; not a complete harness or print recommendation'
bpy.context.scene['main_model_not_updated']=True
for name in changed_parts:
    ss[name].o['candidate_only']='J1 UNAPPROVED; load/contact and wire retention unresolved'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
report=dict(status='PASS' if not hits and not fixed_hits and all(len(x['remaining_components_mm3'])==1 for x in results.values()) else 'FAIL',
    scope='Joined four-wire staging geometry in independent J1 copy only',
    source_blend_sha256=before,source_route_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    wire_od_mm=.6604,wire_surface_gap_requirement_mm=.3,cut_radius_mm=cut_radius,
    changed_existing_ids=changed,unchanged_physical_count=209-len(changed),part_results=results,
    source_hits=hits,fourteen_fixed_wire_hits=fixed_hits,head_pose_count=130,wire_pose_instances=520,
    main_model_applied=False,physical_retention='NOT_TESTED',print_strength='NOT_TESTED',
    contact_area_and_thin_remnants='NOT_TESTED',wire_threading='NOT_TESTED',
    whole_harness='BLOCKED',supplier_cut_length='BLOCKED',
    candidate_blend_sha256=hashlib.sha256((OUT/'candidate.blend').read_bytes()).hexdigest())
(OUT/'screening.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('JOINED_CANDIDATE_COMPLETE',report['status'],len(hits),len(fixed_hits),flush=True)
