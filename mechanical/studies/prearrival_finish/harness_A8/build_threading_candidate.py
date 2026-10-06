"""J2: swept nominal bare-contact transit clearance in an independent copy.

Preserve all original hardware. A padded convex sweep covers interpolation
between temporary insertion stations. It is not final crimped-terminal CAD,
an adopted print, or qualification of a flexible trailing wire.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve();HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent/'terminal_threading'
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record
transit_path=OUT/'transit_screen.json';transit=json.loads(transit_path.read_text())
assert transit['source_blend_sha256']==before
selected=next(r for r in transit['results'] if r['status']=='PASS')
baseline={n:geometry_record(s.o) for n,s in ss.items()}
original={n:s.m for n,s in ss.items()}
targets=['Yaw_Base','Pitch_Yoke']
assert len(ss)==209

pad=.32;sphere=manifold.Manifold.sphere(pad,32)
sm=sphere.to_mesh64();sv=np.array(sm.vert_properties[:,:3]);sf=np.array(sm.tri_verts)
a,b,c=sv[sf[:,0]],sv[sf[:,1]],sv[sf[:,2]];normals=np.cross(b-a,c-a)
inscribed=float(np.min(np.abs(np.sum(normals*a,axis=1))/np.linalg.norm(normals,axis=1)))
box_radius=float(np.linalg.norm(np.array(transit['dimensions_mm'])/2))
lower_error=(16+8*selected['lower_outward_bump_mm']+box_radius)*(math.pi/200)**2/8
upper_error=(16+4.5*selected['upper_outward_bump_mm']+box_radius)*(math.pi/240)**2/8
error=max(lower_error,upper_error)
assert inscribed-error>.3
template=manifold.Manifold.cube(transit['dimensions_mm'],center=True).minkowski_sum(sphere)
transforms=[np.array(t) for t in selected['cases'][0]['transforms_3x4']]
instances=[template.transform(t) for t in transforms]
segments=[]
for i,(a,b) in enumerate(zip(instances,instances[1:])):
    segments.append(manifold.Manifold.batch_hull([a,b]))
    if i%150==0:print('THREAD_SWEEP_HULL',i,len(transforms)-1,round(time.time()-start,1),flush=True)
first=manifold.Manifold.batch_boolean(segments,manifold.OpType.Add)
sweeps=[first.rotate((0,0,90.*i)) for i in range(4)]
print('THREAD_SWEEP_UNION',first.volume(),round(time.time()-start,1),flush=True)

hardware_hits=[];fixed_hits=[]
fixed_solids={n:manifold.Manifold(manifold.Mesh64(vert_properties=r['vertices'],tri_verts=np.asarray(r['triangles'],dtype=np.uint64))) for n,r in fixed.items()}
for angle,sw in zip([45,135,225,315],sweeps):
    bb=np.array(sw.bounding_box())
    for name,s in ss.items():
        if name in targets or np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
        vol=max(0.,float((sw^s.m).volume()))
        if vol>1e-5:hardware_hits.append(dict(azimuth_deg=angle,object=name,intersection_mm3=vol))
    for name,mf in fixed_solids.items():
        f=fixed[name]
        if np.any(bb[:3]>f['hi']) or np.any(bb[3:]<f['lo']):continue
        vol=max(0.,float((sw^mf).volume()))
        if vol>1e-5:fixed_hits.append(dict(azimuth_deg=angle,object=name,intersection_mm3=vol))
report=dict(source_blend_sha256=before,source_transit_sha256=hashlib.sha256(transit_path.read_bytes()).hexdigest(),
    source_script_sha256=hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    hardware_sweep_hits=hardware_hits,fixed_wire_sweep_hits=fixed_hits,
    padding_mm=pad,inscribed_padding_mm=inscribed,maximum_interpolation_error_bound_mm=error,
    nominal_contact_to_source_gap_lower_bound_mm=inscribed-error,
    reference_dimensions_mm=transit['dimensions_mm'],assembly_yaw_pitch_deg=[0,0],
    swept_sections_per_direction=len(segments),unchanged_source_objects_excluding_two_prints=207,
    main_model_applied=False,actual_terminal_dimensions='NOT_TESTED',trailing_wire='NOT_TESTED',
    physical_retention='NOT_TESTED',whole_harness='BLOCKED')
if hardware_hits or fixed_hits:
    report.update(status='BLOCKED',scope='Swept insertion envelope collided; no candidate built')
    (OUT/'candidate_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('THREAD_SWEEP_BLOCKED',hardware_hits,fixed_hits,flush=True)
    raise SystemExit(0)

tool=manifold.Manifold.batch_boolean(sweeps,manifold.OpType.Add)
results={};removed={}
for name in targets:
    j1=np.load(SCRIPT.parent/'joined_entry_candidate'/f'{name}_candidate.npz')
    existing=manifold.Manifold(manifold.Mesh64(vert_properties=j1['vertices_mm'],tri_verts=j1['triangles'].astype(np.uint64)))
    candidate=existing-tool
    assert candidate.status()==manifold.Error.NoError
    kept=[];discarded=[]
    for component in candidate.decompose():
        volume=float(component.volume())
        if abs(volume)<1e-10:
            cv=np.array(component.to_mesh64().vert_properties[:,:3]);centre=cv.mean(0)
            _,_,vh=np.linalg.svd(cv-centre,full_matrices=False)
            plane_error=float(np.max(np.abs((cv-centre)@vh[-1])))
            assert plane_error<1e-6,(name,volume,plane_error)
            discarded.append(dict(volume_mm3=volume,maximum_plane_distance_mm=plane_error,bounds_mm=list(component.bounding_box())))
        else:kept.append(component)
    assert len(kept)==1,(name,[float(c.volume()) for c in kept])
    candidate=kept[0];delta=original[name]-candidate
    components=[float(candidate.volume())]
    removed[name]=delta
    for suffix,m in [('baseline',original[name]),('J1',existing),('candidate',candidate),('removed',delta)]:
        mesh=m.to_mesh64();np.savez_compressed(OUT/f'{name}_{suffix}.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
    obj=ss[name].o;replace_owned(name,candidate);ss[name]=Solid(obj);trees[name]=ss[name].bvh()
    protected=['Yaw_Bearing','Yaw_Anti_Lift_Keeper','Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut',
               'Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut']
    results[name]=dict(removed_from_main_mm3=float(delta.volume()),added_removal_from_J1_mm3=float((existing-candidate).volume()),
        remaining_component_volumes_mm3=components,numerical_coplanar_fragments_removed=discarded,
        removed_to_reference_gaps=[dict(part=n,gap_mm=float(delta.min_gap(original[n],10))) for n in protected])
    print('THREAD_PRINT_CUT',name,results[name]['removed_from_main_mm3'],round(time.time()-start,1),flush=True)

route_path=SCRIPT.parent/'joined_entry_screen.json';route=json.loads(route_path.read_text());wire_hits=[]
for row in route['rows']:
    points=np.asarray(row['curve_mm']);yaw=row['yaw_deg']
    for name,s in ss.items():
        for pitch in (range(-20,26,5) if s.group=='pitch' else [0]):
            if s.group in ['yaw','pitch']:
                inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                local=points@inv[:3,:3].T+inv[:3,3]
            else:local=points
            h=sample_clear(local,.3302,row['error_bound_mm'],[name])
            if h:wire_hits.append(dict(yaw_deg=yaw,pitch_deg=pitch,azimuth_deg=row['azimuth_deg'],**h));break
changed=sorted(n for n,s in ss.items() if baseline[n]!=geometry_record(s.o));assert changed==sorted(targets)
sections={}
for angle in [0,45,90,135]:
    a=math.radians(angle);tr=np.array([[0,0,1,0],[math.cos(a),math.sin(a),0,0],[-math.sin(a),math.cos(a),0,0]])
    layers={n:ss[n].m for n in ['Yaw_Base','Pitch_Yoke','Yaw_Reaction_Link','Yaw_Bearing','Yaw_Servo','Pitch_Servo']}
    layers.update({n+'_baseline':original[n] for n in targets});layers.update({n+'_removed':removed[n] for n in targets})
    sections[str(angle)]={n:[np.asarray(p)[:,[1,0]].tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}
(OUT/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')
for i,m in enumerate(sweeps):
    mesh=m.to_mesh64();np.savez_compressed(OUT/f'terminal_sweep_{i}.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
bpy.context.scene['independent_unapproved_study']='A8 J2: nominal loose-contact transit clearance; retention, trailing-wire behaviour and final crimp envelope unresolved'
bpy.context.scene['main_model_not_updated']=True
for n in targets:ss[n].o['candidate_only']='J2 UNAPPROVED; nominal contact insertion and local wires only'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
report.update(status='PASS' if not wire_hits else 'FAIL',scope='Independent J2; swept nominal contact and installed staging wires only',
    part_results=results,changed_existing_ids=changed,unchanged_physical_count=207,
    wire_pose_instances=520,head_motion_poses=130,installed_wire_hits=wire_hits,
    source_installed_route_sha256=hashlib.sha256(route_path.read_bytes()).hexdigest(),
    candidate_blend_sha256=hashlib.sha256((OUT/'candidate.blend').read_bytes()).hexdigest(),
    strength_and_thin_remnants='NOT_TESTED',contact_post_crimp_profile='NOT_TESTED')
(OUT/'candidate_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('THREAD_J2_COMPLETE',report['status'],round(time.time()-start,1),flush=True)
