"""Consistent larger bare-contact space in the existing unadopted neck study.

Only subtract the bounded contact sweep from the same two candidate prints.
No source or main-model modification, new hole location, hardware movement,
manufacturing release, or strength qualification is performed here.
"""
from pathlib import Path
LNC_SCRIPT = Path(__file__).resolve()
LNC_HELPER = LNC_SCRIPT.parent / 'plan_h06_documented_mates.py'
__file__ = str(LNC_HELPER)
exec(compile(LNC_HELPER.read_text().split('\nports=json.loads',1)[0], str(LNC_HELPER), 'exec'), globals())
__file__ = str(LNC_SCRIPT)
LNC_A8 = LNC_SCRIPT.parent
LNC_OUT = LNC_A8 / 'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
LNC_OUT.mkdir(exist_ok=True)
LNC_START = time.time()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
protected = {str(p.relative_to(PROJECT)): sha(p) for p in [source, PROJECT/'config/geometry.json', PROJECT/'contracts/mechanical_interfaces.json', PROJECT/'contracts/components.json']}
from validate_head_cleanup import geometry_record
from interface_completion import replace_owned
before = {o.name: geometry_record(o) for o in parts()}
replacement_paths = {
    'Yaw_Base': LNC_A8/'cam_anchors/candidate_v3/cleaned/Yaw_Base.npz',
    'Pitch_Yoke': LNC_A8/'cam_anchors/candidate_v3/cleaned/Pitch_Yoke.npz',
    'Pitch_Cradle': LNC_A8/'cam_pitch_anchor/connector_anchor/Pitch_Cradle.npz',
}
def read_m(path):
    a = np.load(path)
    return manifold.Manifold(manifold.Mesh64(a['vertices_mm'], a['triangles'].astype(np.uint64)))
def save_m(name, m):
    a = m.to_mesh64()
    np.savez_compressed(LNC_OUT/(name+'.npz'), vertices_mm=np.asarray(a.vert_properties[:,:3]), triangles=np.asarray(a.tri_verts))
current = {n: s.m for n,s in ss.items()}
current.update({n: read_m(p) for n,p in replacement_paths.items()})
feed_path = LNC_OUT/'lower_bend/screen.json'
feed = json.loads(feed_path.read_text())
assert feed['status']=='PASS' and feed['source_main_sha256']==source_hash
assert feed['selected_radius_mm']==10. and feed['selected_lower_top_z_mm']==148.
path_file=LNC_OUT/'lower_bend/selected_path.npz'
assert sha(path_file)==feed['selected_path_sha256']
path_data=np.load(path_file)
trajectory=path_data['radial_z_axis_angle'];labels=path_data['segment_names'].tolist()
cases=[]
for phase in (45,135,225,315):
    phi=math.radians(phase);er=np.array([math.cos(phi),math.sin(phi),0.]);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
    tr=[]
    for r,z,a in trajectory:
        axis=er*math.sin(a)+ez*math.cos(a);x=er*math.cos(a)-ez*math.sin(a)
        tr.append(np.column_stack([x,et,axis,r*er+z*ez+axis*3.9/2]).tolist())
    cases.append(dict(phase_deg=phase,contact_transforms_3x4=tr))
LNC_DIMS = np.array([1., 1.8, 4.1])
LNC_PAD = .32
sphere = manifold.Manifold.sphere(LNC_PAD, 48)
sm = sphere.to_mesh64(); vs = np.asarray(sm.vert_properties[:,:3]); faces = np.asarray(sm.tri_verts)
aa,bb,cc = vs[faces[:,0]],vs[faces[:,1]],vs[faces[:,2]]
nn = np.cross(bb-aa,cc-aa)
inner = float(np.min(np.abs(np.einsum('ij,ij->i',aa,nn))/np.linalg.norm(nn,axis=1)))
da = float(np.max(np.abs(np.diff(trajectory[:,2]))))
# A point of the terminal follows at most an R10 circle plus a rigid vector no longer
# than its full length, half diagonal and padding. Sagitta bound is outward.
error = (10.+LNC_DIMS[2]+np.linalg.norm(LNC_DIMS[:2]/2)+LNC_PAD)*da**2/8 + 1e-6
assert inner-error > .3
template = manifold.Manifold.cube(LNC_DIMS.tolist(),center=True).minkowski_sum(sphere)
alltargets = dict(current)
alltargets.update({'Plug_'+n:s.m for n,s in plug.items()})
alltargets.update({'fixed_wire_'+n:s['m'] for n,s in fixed.items()})
boxes = {n:np.array(m.bounding_box()) for n,m in alltargets.items()}
def hits(shape, excluded=()):
    box=np.array(shape.bounding_box()); result=[]
    for n,m in alltargets.items():
        if n in excluded: continue
        b=boxes[n]
        if np.any(box[:3]>b[3:]) or np.any(b[:3]>box[3:]): continue
        volume=max(0.,float((shape^m).volume()))
        if volume>1e-5: result.append(dict(obstacle=n,intersection_mm3=volume))
    return result

sweeps=[]; sweep_rows=[]; wire_sweeps=[]; wire_rows=[]; wire_curves={}
wire_sphere=manifold.Manifold.sphere(.65,48)
wire_error=10.*da**2/8+1e-6
wire_gap_bound=inner/LNC_PAD*.65-wire_error-.3302
assert wire_gap_bound>.3
for case in cases:
    ts=[]
    for matrix in case['contact_transforms_3x4']:
        t=np.asarray(matrix).copy()
        t[:,3] += t[:,2]*(LNC_DIMS[2]-3.9)/2
        ts.append(t)
    instances=[template.transform(t) for t in ts]
    spans=[]; i=0
    while i < len(ts)-1:
        j=i+1
        while j+1<len(ts) and np.max(np.abs(ts[j+1][:,:3]-ts[i][:,:3]))<1e-12:
            u=ts[j+1][:,3]-ts[i][:,3]; v=ts[j][:,3]-ts[i][:,3]
            if np.linalg.norm(np.cross(u,v))>1e-9: break
            j+=1
        spans.append((i,j)); i=j
    pieces=[manifold.Manifold.batch_hull([instances[i],instances[j]]) for i,j in spans]
    sweep=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    conflicts=hits(sweep, {'Yaw_Base','Pitch_Yoke'})
    save_m('contact_sweep_'+str(case['phase_deg']),sweep)
    row=dict(phase_deg=case['phase_deg'],spans=len(spans),status='PASS' if not conflicts else 'BLOCKED',conflicts=conflicts)
    sweep_rows.append(row);sweeps.append(sweep)
    print('LARGER_NECK_SWEEP',row,round(time.time()-LNC_START,2),flush=True)

    # The attached wire is a prefix of the temporary guide. After the contact
    # clears the neck, R10/Z148 can relax to the old R8/Z147 guide with a loose
    # body end. Matching arc angles makes the centreline affine in this move.
    phase=math.radians(case['phase_deg']);er=np.array([math.cos(phase),math.sin(phase),0.]);ez=np.array([0.,0.,1.])
    new_points=trajectory[:,0,None]*er+trajectory[:,1,None]*ez
    old_points=new_points.copy()
    for index,((r,z,a),label) in enumerate(zip(trajectory,labels)):
        if label=='body_free_lead':old_points[index]=(r-2)*er+139.*ez
        elif label=='lower_bend':old_points[index]=(7.6+8.*(1-math.cos(a)))*er+(147.+8.*math.sin(a))*ez
        elif label=='central_straight':old_points[index]=r*er+(147.+(z-148.)*31./30.)*ez
    wp=[manifold.Manifold.batch_hull([wire_sphere.translate(p.tolist()) for p in
                                    (new_points[i],new_points[j],old_points[i],old_points[j])]) for i,j in spans]
    wire_sweep=manifold.Manifold.batch_boolean(wp,manifold.OpType.Add)
    wire_conflicts=hits(wire_sweep,{'Yaw_Base','Pitch_Yoke'})
    wire_rows.append(dict(phase_deg=case['phase_deg'],status='PASS' if not wire_conflicts else 'BLOCKED',conflicts=wire_conflicts))
    wire_sweeps.append(wire_sweep);save_m('wire_relaxation_'+str(case['phase_deg']),wire_sweep)
    wire_curves['phase'+str(case['phase_deg'])+'_new']=new_points
    wire_curves['phase'+str(case['phase_deg'])+'_old']=old_points
    print('LARGER_NECK_ATTACHED_WIRE',wire_rows[-1],flush=True)

np.savez_compressed(LNC_OUT/'wire_relaxation_curves.npz',**wire_curves)
tool=manifold.Manifold.batch_boolean(sweeps+wire_sweeps,manifold.OpType.Add)
changed=[];local_rows=[]
critical=[n for n in current if n.startswith(('Yaw_','Head_Yaw_Ear_')) and n!='Yaw_Base']
critical += ['Pitch_Servo','Pitch_Bearing_L','Pitch_Bearing_R','Head_Pitch_Ear_0_Screw','Head_Pitch_Ear_1_Screw']
for n in ('Yaw_Base','Pitch_Yoke'):
    old=current[n]; raw=old-tool; kept=[];discarded=[]
    for component in raw.decompose():
        volume=float(component.volume())
        if abs(volume)<1e-7:
            vertices=np.asarray(component.to_mesh64().vert_properties[:,:3]);centroid=vertices.mean(0)
            _,_,vh=np.linalg.svd(vertices-centroid,full_matrices=False)
            plane_error=float(np.max(np.abs((vertices-centroid)@vh[-1])))
            storage_ulp=float(np.max(np.spacing(np.abs(vertices).astype(np.float32))))
            # Boolean coincidences below the actual Blender coordinate ULP
            # cannot encode a physical printed island. Keep the proof and its
            # bound explicit; do not relax the 0.3 mm clearance requirement.
            assert plane_error<=2*storage_ulp,(n,volume,plane_error,storage_ulp)
            discarded.append(dict(volume_mm3=volume,maximum_plane_deviation_mm=plane_error,
                                  maximum_Blender_coordinate_ULP_mm=storage_ulp))
        else:kept.append(component)
    assert len(kept)==1,(n,[float(c.volume()) for c in kept])
    new=kept[0];removed=old-new;added=new-old
    components=[float(x.volume()) for x in new.decompose()]
    save_m(n+'_before',old);save_m(n,new);save_m(n+'_removed',removed)
    near=[]
    for other in critical:
        if other==n:continue
        gap=float(removed.min_gap(current[other],5.))
        if gap<5.:near.append(dict(reference=other,removed_to_reference_gap_mm=gap))
    row=dict(part=n,removed_mm3=float(removed.volume()),added_mm3=max(0.,float(added.volume())),
             source_volume_mm3=float(old.volume()),remaining_volume_mm3=float(new.volume()),
             remaining_components_mm3=components,kernel_status=str(new.status()),
             removed_bounds_mm=list(removed.bounding_box()),nearby_reference_surfaces=near,
             discarded_numerical_zero_planes=discarded)
    assert row['added_mm3']<1e-7 and len(components)==1 and new.status()==manifold.Error.NoError,row
    local_rows.append(row);changed.append(n)
    print('LARGER_NECK_PART',row,flush=True)
    replace_owned(n,new)
    # Blender float32 storage is audited explicitly against the source kernel.
    stored=Solid(ss[n].o).m
    delta=max(0.,float((stored-new).volume()))+max(0.,float((new-stored).volume()))
    row['stored_symmetric_difference_mm3']=delta
    row['stored_components_mm3']=[float(x.volume()) for x in stored.decompose()]
    row['stored_kernel_status']=str(stored.status())
    save_m(n+'_stored',stored)

# Other inherited candidate changes are source-preserved; do not incorporate
# the older J2 replacements made by the helper into this review blend.
replace_owned('Pitch_Cradle',current['Pitch_Cradle'])
sections={}
er=np.array([2**-.5,2**-.5,0.]);et=np.array([-2**-.5,2**-.5,0.]);ez=np.array([0.,0.,1.])
rtz=np.column_stack([er,ez,et]).T
for n in changed:
    layers={k:read_m(LNC_OUT/(n+suffix+'.npz')) for k,suffix in [('before','_before'),('after',''),('removed','_removed')]}
    sections[n]={}
    for z in ([143.,144.,145.,146.,147.] if n=='Yaw_Base' else [153.,178.,184.,188.,190.]):
        sections[n]['Z'+str(z)]={k:[p.tolist() for p in m.slice(z).to_polygons()] for k,m in layers.items()}
    sections[n]['radial45']={k:[p.tolist() for p in m.transform(np.column_stack([rtz,np.zeros(3)])).slice(0).to_polygons()] for k,m in layers.items()}
(LNC_OUT/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')
bpy.context.scene['independent_unapproved_study']='Larger ASSUMED contact allocation in existing CAM feed channels; not approved for main model'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(LNC_OUT/'candidate.blend'))
after={o.name:geometry_record(o) for o in parts()}
expected={PREFIX+n for n in replacement_paths}
changed_source_names={n for n in before if before[n]!=after[n]}
assert changed_source_names<=expected,changed_source_names
report=dict(status='PASS' if all(r['status']=='PASS' for r in sweep_rows+wire_rows) else 'BLOCKED',
    scope='Bounded continuous contact sweep and exact subtraction of two unadopted channel candidates; not whole assembly or strength',
    script_sha256=sha(LNC_SCRIPT),helper_sha256=sha(LNC_HELPER),source_main_sha256=source_hash,
    protected_sources=protected,source_feed_sha256=sha(feed_path),
    inherited_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacement_paths.items()},
    mate_dimensions_sha256=sha(LNC_A8/'amass_mating/received_dimensions.json'),source_fixed_wires_sha256=sha(fixed_path),
    source_objects=len(ss),mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    contact_dimensions_mm=LNC_DIMS.tolist(),contact_evidence='ASSUMED requested maximum space; manufacturer post-crimp outline remains unavailable',
    padding_mm=LNC_PAD,padding_inscribed_radius_mm=inner,interpolation_error_bound_mm=error,
    nominal_contact_source_gap_bound_mm=inner-error,sweep_rows=sweep_rows,parts=local_rows,
    lower_bend_radius_mm=10.,lower_bend_top_z_mm=148.,wire_relaxation_rows=wire_rows,
    wire_surface_gap_bound_mm=wire_gap_bound,wire_interpolation_error_bound_mm=wire_error,
    minimum_wire_bend_radius_during_relaxation_mm=8.,required_wire_bend_radius_mm=REQUIRED_R,
    wire_length_supply_during_relaxation_mm=math.pi-1.,wire_supply_note='Extra temporary guide length is supplied by an unmodeled loose body tail; not a new cut-length allowance.',
    temporary_guide_path_sha256=sha(path_file),wire_curves_sha256=sha(LNC_OUT/'wire_relaxation_curves.npz'),
    source_physical_objects_preserved=len(before),changed_candidate_prints=changed,
    main_source_changes_from_inherited_candidates=sorted(changed_source_names),
    main_geometry_changed=False,candidate_blend_sha256=sha(LNC_OUT/'candidate.blend'),
    stored_sweep_recheck='NOT_TESTED',continuous_trailing_wire='Neck prefixes and affine R10/Z148 to R8/Z147 relaxation checked; full loose body tail remains NOT_TESTED',
    seating_and_body_supply='NOT_TESTED',structural_walls='NOT_TESTED',strength='NOT_TESTED',
    whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-LNC_START)
(LNC_OUT/'construction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('LARGER_NECK_CANDIDATE_DONE',report['status'],round(time.time()-LNC_START,2),flush=True)
