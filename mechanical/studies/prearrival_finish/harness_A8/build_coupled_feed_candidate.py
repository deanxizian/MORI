"""J3 independent neck feed: rigid SH reference plus attached R8 wire.

Construct bounded continuous sweeps, then cut only the two independently
studied prints from J1.  This does not adopt, print, or qualify the assembly.
"""
from pathlib import Path
BUILD_SCRIPT=Path(__file__).resolve();BUILD_DIR=BUILD_SCRIPT.parent
BUILD_HELPER=BUILD_DIR/'plan_h06_documented_mates.py';__file__=str(BUILD_HELPER)
exec(compile(BUILD_HELPER.read_text().split('\nports=json.loads',1)[0],str(BUILD_HELPER),'exec'),globals())
__file__=str(BUILD_SCRIPT);BUILD_START=time.time();OUT=BUILD_DIR/'assembly_feed_v3'
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record
feed_path=OUT/'coupled_feed_screen.json';feed=json.loads(feed_path.read_text())
chosen=next(r for r in feed['tested_cases'] if r['radius_mm']==feed['selected_radius_mm'])
assert chosen['status_with_mates']=='PASS'
baseline_records={n:geometry_record(s.o) for n,s in ss.items()}
old_j2={n:ss[n].m for n in ['Yaw_Base','Pitch_Yoke']}
pad=.32;sphere=manifold.Manifold.sphere(pad,32)
sp=sphere.to_mesh64();v=np.array(sp.vert_properties[:,:3]);f=np.array(sp.tri_verts)
a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];norm=np.cross(b-a,c-a)
inscribed=float(np.min(np.abs(np.einsum('ij,ij->i',a,norm))/np.linalg.norm(norm,axis=1)))
path=np.array(chosen['radial_z_axis_angle']);da=float(np.abs(np.diff(path[:,2])).max())
# All rotating corners consist of an R8 arc plus a forward rigid length<=3.9,
# half cross-section diagonal and padding. Straight spans interpolate exactly.
contact_error=(8.+3.9+math.hypot(.4,.675)+pad)*da**2/8
assert inscribed-contact_error>.3
nominal=manifold.Manifold.cube(feed['reference_contact_dimensions_mm'],center=True)
template=nominal.minkowski_sum(sphere)
tr=[np.array(x) for x in chosen['cases'][0]['contact_transforms_3x4']]
instances=[template.transform(t) for t in tr]
# Merge exactly straight, constant-orientation intervals before boolean union.
# Hundreds of coincident capsule faces on the long straight had produced
# float32 slivers. Their single endpoint hull is the same convex swept solid.
intervals=[];i=0
while i<len(tr)-1:
    j=i+1
    while j+1<len(tr) and np.max(np.abs(tr[j+1][:,:3]-tr[i][:,:3]))<1e-12:
        a=tr[j+1][:,3]-tr[i][:,3];b=tr[j][:,3]-tr[i][:,3]
        if np.linalg.norm(np.cross(a,b))>1e-9:break
        j+=1
    intervals.append((i,j));i=j
pieces=[manifold.Manifold.batch_hull([instances[i],instances[j]]) for i,j in intervals]
first=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
contact_sweeps=[first.rotate((0.,0.,90*i)) for i in range(4)]
print('COUPLED_SWEEP',len(pieces),round(time.time()-BUILD_START,2),flush=True)

# Every tail is a prefix of this R8 guide, fed from a loose lower end. Capsules
# cover each chord; the inscribed sphere exceeds wire radius+gap+sagitta.
wire_pad=.645;wire_sphere=manifold.Manifold.sphere(wire_pad,32)
wire_inner=inscribed/pad*wire_pad
assert wire_inner-chosen['curve_chord_error_bound_mm']>.3302+.3
points=np.array(chosen['cases'][0]['wire_rear_curve_mm']);wp=[]
for i,j in intervals:
    wp.append(manifold.Manifold.batch_hull([wire_sphere.translate(points[i].tolist()),wire_sphere.translate(points[j].tolist())]))
wire_first=manifold.Manifold.batch_boolean(wp,manifold.OpType.Add)
wire_sweeps=[wire_first.rotate((0.,0.,90*i)) for i in range(4)]
# The first post-feed operation has zero angular slack: shift r7.6->6.8,
# upper turn Z178->179, and the loose upper end Z202.1->206. With matching
# path parameters every intermediate point is affine in the shift fraction.
# Hulls of four endpoint balls cover the entire bilinear segment patch; this
# avoids certifying just the two endpoint shapes or opening an arbitrary box.
target_points=points.copy();er=np.array([math.sqrt(.5),math.sqrt(.5),0.])
upper_old=178.+16*math.sin(math.pi/3);upper_new=upper_old+1.
for i,(point,label) in enumerate(zip(points,chosen['segment_names'])):
    target_points[i]=point-.8*er
    if label=='central_straight':target_points[i,2]=147+(point[2]-147)*32/31
    elif label.startswith('upper_R8'):target_points[i,2]=point[2]+1.
    elif label=='upper_free_end':target_points[i,2]=upper_new+(point[2]-upper_old)*(206-upper_new)/(202.1-upper_old)
relax_pieces=[]
for i,j in intervals:
    relax_pieces.append(manifold.Manifold.batch_hull([wire_sphere.translate(p.tolist())
        for p in [points[i],points[j],target_points[i],target_points[j]]]))
relax_first=manifold.Manifold.batch_boolean(relax_pieces,manifold.OpType.Add)
relax_sweeps=[relax_first.rotate((0.,0.,90*i)) for i in range(4)]
tools_by_phase=[c+w+r for c,w,r in zip(contact_sweeps,wire_sweeps,relax_sweeps)]
hits=[]
for phase,m in zip([45,135,225,315],tools_by_phase):
    bb=np.array(m.bounding_box())
    for name,s in obstacles.items():
        if name in old_j2 or np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
        vol=max(0.,float((m^s.m).volume()))
        if vol>1e-6:hits.append({'phase_deg':phase,'object':name,'overlap_mm3':vol})
    for name,s in fixed.items():
        if np.any(bb[:3]>s['hi']) or np.any(bb[3:]<s['lo']):continue
        vol=max(0.,float((m^s['m']).volume()))
        if vol>1e-6:hits.append({'phase_deg':phase,'object':name,'overlap_mm3':vol})
assert not hits,hits
print('COUPLED_SOURCES_PASS',round(time.time()-BUILD_START,2),flush=True)

cut=manifold.Manifold.batch_boolean(tools_by_phase,manifold.OpType.Add)
parts=[]
for name in old_j2:
    j1_path=BUILD_DIR/'joined_entry_candidate'/f'{name}_candidate.npz'
    j1=np.load(j1_path);old=manifold.Manifold(manifold.Mesh64(vert_properties=j1['vertices_mm'],tri_verts=j1['triangles'].astype(np.uint64)))
    raw=old-cut;kept=[];discarded=[]
    for m in raw.decompose():
        vol=float(m.volume())
        if abs(vol)<1e-7:
            vv=np.array(m.to_mesh64().vert_properties[:,:3]);centre=vv.mean(0);_,_,vh=np.linalg.svd(vv-centre,full_matrices=False)
            distance=float(np.max(np.abs((vv-centre)@vh[-1])))
            assert distance<1e-6,(name,vol,distance)
            discarded.append({'volume_mm3':vol,'max_plane_distance_mm':distance})
        else:kept.append(m)
    assert len(kept)==1,(name,[float(m.volume()) for m in kept])
    candidate=kept[0];assert candidate.status()==manifold.Error.NoError
    obj=ss[name].o;replace_owned(name,candidate);ss[name]=Solid(obj);trees[name]=ss[name].bvh()
    for suffix,m in [('candidate',candidate),('J1',old),('J2',old_j2[name]),('removed_from_J1',old-candidate),
                     ('added_from_J2',candidate-old_j2[name]),('removed_from_J2',old_j2[name]-candidate)]:
        mm=m.to_mesh64();np.savez_compressed(OUT/f'{name}_{suffix}.npz',vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))
    parts.append({'part':name,'volume_mm3':float(candidate.volume()),'additional_removal_from_J1_mm3':float((old-candidate).volume()),
        'added_from_J2_mm3':float((candidate-old_j2[name]).volume()),'removed_from_J2_mm3':float((old_j2[name]-candidate).volume()),
        'solid_components':1,'discarded_numerical_planes':discarded,
        'raw_float32_storage_audit':'NOT_TESTED','minimum_wall_and_strength':'NOT_TESTED'})
    print('COUPLED_PRINT',parts[-1],flush=True)

for i,m in enumerate(contact_sweeps):
    mm=m.to_mesh64();np.savez_compressed(OUT/f'contact_sweep_{i}.npz',vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))
for i,m in enumerate(wire_sweeps):
    mm=m.to_mesh64();np.savez_compressed(OUT/f'wire_sweep_{i}.npz',vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))
for i,m in enumerate(relax_sweeps):
    mm=m.to_mesh64();np.savez_compressed(OUT/f'relaxation_sweep_{i}.npz',vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))

# Check the materialised J3 meshes and physical/source assignment, then save a
# distinct file. The runtime closed-solid results are not a reload/topology pass.
changes=sorted(n for n,s in ss.items() if baseline_records[n]!=geometry_record(s.o))
assert changes==['Pitch_Yoke','Yaw_Base']
bpy.context.scene['independent_unapproved_study']='J3 coupled loose SH terminal and trailing R8 wire; assembly relaxation and anchors unresolved'
bpy.context.scene['main_model_not_updated']=True
for name in changes:ss[name].o['candidate_only']='J3 UNAPPROVED coupled-feed clearance; walls and installed-route replay pending'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'status':'PASS','scope':'Continuous nominal contact+trailing guide envelope against207 sources,29 mates and14 static wires; two prints independent',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(BUILD_SCRIPT),'source_helper_sha256':sha(BUILD_HELPER),
    'source_feed_sha256':sha(feed_path),'source_J1':{n:sha(BUILD_DIR/'joined_entry_candidate'/f'{n}_candidate.npz') for n in old_j2},
    'candidate_blend_sha256':sha(OUT/'candidate.blend'),'changed_existing_ids':changes,'unchanged_source_objects':207,
    'contact_gap_lower_bound_mm':inscribed-contact_error,'contact_interpolation_error_bound_mm':contact_error,
    'tail_gap_lower_bound_mm':wire_inner-chosen['curve_chord_error_bound_mm']-.3302,
    'radial_shift_envelope':'Continuous affine reshaping, from four endpoint spheres per parameter interval',
    'radial_shift_error_bound_mm':chosen['curve_chord_error_bound_mm'],
    'segments_per_phase':len(pieces),'original_station_intervals':len(tr)-1,
    'merged_straight_intervals':[[i,j] for i,j in intervals if j>i+1],
    'phases':4,'source_hits':hits,'parts':parts,
    'main_model_applied':False,'wire_radius_during_feed_mm':chosen['radius_mm'],'wire_bend_radius_mm':8.,
    'installed_routing_replay':'NOT_TESTED','four_wire_installation_order':'NOT_TESTED',
    'relaxation_to_installed_routes':'NOT_TESTED','fixed_anchor_design':'NOT_TESTED',
    'raw_storage_reload':'NOT_TESTED','complete_harness':'BLOCKED','manufacturing_release':False,
    'elapsed_s':time.time()-BUILD_START}
(OUT/'candidate_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('COUPLED_J3_COMPLETE',report['status'],round(time.time()-BUILD_START,2),flush=True)
