"""Reload J2, audit raw print topology and add all mating allocations.

Keep the original 209-source PASS scoped to its original evidence. The 29
extra plug allocations may invalidate a complete-assembly claim; do not waive
them by treating independently planned connectors as absent.
"""
from pathlib import Path
AUDIT_SCRIPT=Path(__file__).resolve();AUDIT_DIR=AUDIT_SCRIPT.parent
helper=AUDIT_DIR.parent/'harness_A2/check_static.py';__file__=str(helper)
exec(compile(helper.read_text().split('MARGIN =')[0],str(helper),'exec'),globals())
__file__=str(AUDIT_SCRIPT)
from validate_head_cleanup import geometry_record
from validate import rigidtr
from collections import Counter
out=AUDIT_DIR/'terminal_threading';before_records={n:geometry_record(s.o) for n,s in ss.items()}
report=json.loads((out/'candidate_screen.json').read_text())
assert source_hash==report['source_blend_sha256']
CLEANED='--cleaned' in sys.argv
audit_out=out/'cleaned' if CLEANED else out
candidate_source=audit_out/'candidate.blend'
candidate_record=json.loads((audit_out/'storage_rebuild.json').read_text()) if CLEANED else report
assert hashlib.sha256(candidate_source.read_bytes()).hexdigest()==candidate_record['candidate_blend_sha256']
# Preserve standalone numeric plug solids/trees before loading the candidate.
mates={n:{'v':s.v.copy(),'f':s.f.copy(),'m':s.m,'lo':s.lo.copy(),'hi':s.hi.copy(),'tree':s.bvh()}
       for n,s in plug.items()}
bpy.ops.wm.open_mainfile(filepath=str(candidate_source))
load_collections();assembled();bpy.context.view_layer.update()
current={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
after_records={n:geometry_record(o) for n,o in current.items()}
changed=sorted(n for n in current if after_records[n]!=before_records[n])
assert set(current)==set(before_records) and changed==['Pitch_Yoke','Yaw_Base']
topology=[]
for name in changed:
    o=current[name];o.data.calc_loop_triangles()
    v=np.array([tuple(o.matrix_world@p.co) for p in o.data.vertices]);f=np.array([tuple(t.vertices) for t in o.data.loop_triangles])
    edges=Counter();orientation=Counter();adj=[set() for _ in v]
    for tri in f:
        for a,b in zip(tri,np.roll(tri,-1)):
            key=tuple(sorted((int(a),int(b))));edges[key]+=1;orientation[key]+=1 if a<b else -1
            adj[a].add(int(b));adj[b].add(int(a))
    remaining=set(int(i) for i in f.ravel());component_sizes=[]
    while remaining:
        todo=[remaining.pop()];size=0
        while todo:
            i=todo.pop();size+=1;found=adj[i]&remaining;remaining-=found;todo+=list(found)
        component_sizes.append(size)
    areas=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
    m=manifold.Manifold(manifold.Mesh64(vert_properties=v,tri_verts=f.astype(np.uint64)))
    expected=np.load(audit_out/f'{name}.npz' if CLEANED else out/f'{name}_candidate.npz');em=manifold.Manifold(manifold.Mesh64(
        vert_properties=expected['vertices_mm'],tri_verts=expected['triangles'].astype(np.uint64)))
    mismatch=max(0,float((m-em).volume()))+max(0,float((em-m).volume()))
    row={'part':name,'raw_vertices':len(v),'raw_triangles':len(f),'non_two_face_edges':sum(n!=2 for n in edges.values()),
         'orientation_inconsistencies':sum(n!=0 for n in orientation.values()),'zero_area_faces':int(np.sum(areas<1e-14)),
         'minimum_face_area_mm2':float(areas.min()),'connected_vertex_counts':component_sizes,
         'manifold_status':str(m.status()),'volume_mm3':float(m.volume()),
         'saved_vs_construction_symmetric_difference_mm3':mismatch,
         'scope':'Reloaded Blender mesh. Topology is not minimum wall/strength qualification.'}
    row['status']='PASS' if (row['non_two_face_edges']==row['orientation_inconsistencies']==row['zero_area_faces']==0
        and len(component_sizes)==1 and m.status()==manifold.Error.NoError and mismatch<.05) else 'FAIL'
    topology.append(row)

route=json.loads((AUDIT_DIR/'joined_entry_screen.json').read_text())
clean_source_hits=[]
if CLEANED:
    ss={n:Solid(o) for n,o in current.items()};source_trees={n:s.bvh() for n,s in ss.items()}
    for row in route['rows']:
        pts=np.asarray(row['curve_mm']);allowance=.3302+.3+np.linalg.norm(np.diff(pts,axis=0),axis=1).max()/2+row['error_bound_mm']+1e-4
        for name,s in ss.items():
            for pitch in (range(-20,26,5) if s.group=='pitch' else [0]):
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(row['yaw_deg'],pitch if s.group=='pitch' else 0)))
                    points=pts@inv[:3,:3].T+inv[:3,3]
                else:points=pts
                mask=np.all(points>=s.lo-allowance,axis=1)&np.all(points<=s.hi+allowance,axis=1)
                hit=None
                for p in points[mask]:
                    d=source_trees[name].find_nearest(Vector(p))[3]
                    if d<allowance:hit={'object':name,'point_mm':p.tolist(),'distance_mm':d};break
                if not hit and np.all(points>=s.lo) and np.all(points<=s.hi):
                    tiny=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
                    if (tiny^s.m).volume()>tiny.volume()/2:hit={'object':name,'inside':True}
                if hit:clean_source_hits.append({'yaw_deg':row['yaw_deg'],'pitch_deg':pitch,'azimuth_deg':row['azimuth_deg'],**hit})
wire_checks=[]
for row in route['rows']:
    pts=np.asarray(row['curve_mm']);delta=row['error_bound_mm']
    allowance=.3302+.3+np.linalg.norm(np.diff(pts,axis=0),axis=1).max()/2+delta+1e-4
    hits=[]
    for n,s in mates.items():
        mask=np.all(pts>=s['lo']-allowance,axis=1)&np.all(pts<=s['hi']+allowance,axis=1)
        distances=[(float(s['tree'].find_nearest(Vector(p))[3]),p) for p in pts[mask]]
        if distances:
            d,p=min(distances,key=lambda pair:pair[0])
            if d<allowance:hits.append({'plug':n,'distance_mm':d,'point_mm':p.tolist(),
                                       'required_sampled_clearance_mm':float(allowance)})
        if np.all(pts>=s['lo']) and np.all(pts<=s['hi']):
            tiny=manifold.Manifold.sphere(.01,16).translate(pts[0].tolist())
            if (tiny^s['m']).volume()>tiny.volume()/2:hits.append({'plug':n,'inside':True})
    wire_checks.append({'yaw_deg':row['yaw_deg'],'azimuth_deg':row['azimuth_deg'],
                        'status':'BLOCKED' if hits else 'PASS','hits':hits})
sweep_checks=[]
for i,angle in enumerate([45,135,225,315]):
    raw=np.load(out/f'terminal_sweep_{i}.npz');sweep=manifold.Manifold(manifold.Mesh64(
        vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
    hits=[]
    for n,s in mates.items():
        overlap=max(0.,float((sweep^s['m']).volume()))
        if overlap>1e-5:hits.append({'plug':n,'padded_sweep_overlap_mm3':overlap})
    sweep_checks.append({'azimuth_deg':angle,'status':'BLOCKED' if hits else 'PASS','hits':hits})
result={'status':'PASS' if not clean_source_hits and all(x['status']=='PASS' for x in topology+wire_checks+sweep_checks) else 'BLOCKED',
    'scope':'Reloaded J2 geometry and supplementary mating-envelope audit, not released harness',
    'source_blend_sha256':source_hash,'source_candidate_sha256':candidate_record['candidate_blend_sha256'],
    'source_script_sha256':hashlib.sha256(AUDIT_SCRIPT.read_bytes()).hexdigest(),
    'source_original_check_sha256':hashlib.sha256((out/'candidate_screen.json').read_bytes()).hexdigest(),
    'source_mated_review_sha256':hashlib.sha256((PROJECT/'mechanical/studies/prearrival_preparation/mated_connector_review.json').read_bytes()).hexdigest(),
    'changed_existing_ids':changed,'unchanged_physical_count':207,'raw_mesh_checks':topology,
    'normalized_storage':CLEANED,'cleaned_installed_source_check':{'status':('FAIL' if clean_source_hits else 'PASS') if CLEANED else 'NOT_APPLICABLE',
      'source_count':209,'head_pose_count':130,'wire_pose_instances':520,'hits':clean_source_hits},
    'mating_allocation_count':len(mates),'installed_wire_vs_mates':wire_checks,'temporary_contact_sweep_vs_mates':sweep_checks,
    'main_geometry_changed':False,'physical_retention':'NOT_TESTED','complete_harness':'BLOCKED',
    'limits':['Mating shapes include conservative full-unengaged plug/header allocations and unknown actual engagement depth.',
       'A blocked allocation is not proof of a physical clash; it must not be omitted from complete-assembly clearance.',
       'Threading before installing body plugs is an unevaluated alternative, not an approved assembly instruction.',
       'Original 209-source/14-wire sweep remains valid only in that explicitly limited scope.']}
(audit_out/'reloaded_mated_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('J2_RELOAD_AND_MATES',result['status'],[(x['part'],x['status']) for x in topology],
      sum(r['status']!='PASS' for r in wire_checks),sweep_checks,flush=True)
