"""Reload J3, check its stored topology, running wires and feed envelopes."""
from pathlib import Path
VERIFY_SCRIPT=Path(__file__).resolve();VERIFY_DIR=VERIFY_SCRIPT.parent
VERIFY_HELPER=VERIFY_DIR/'plan_h06_documented_mates.py';__file__=str(VERIFY_HELPER)
exec(compile(VERIFY_HELPER.read_text().split('\nports=json.loads',1)[0],str(VERIFY_HELPER),'exec'),globals())
__file__=str(VERIFY_SCRIPT);VERIFY_START=time.time();OUT=VERIFY_DIR/'assembly_feed_v3'
import collections
from validate_head_cleanup import geometry_record
from validate import rigidtr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
storage=json.loads((OUT/'cleaned/storage.json').read_text());construction=json.loads((OUT/'candidate_screen.json').read_text())
assert storage['source_candidate_sha256']==sha(OUT/'candidate.blend')
assert storage['candidate_blend_sha256']==sha(OUT/'cleaned/candidate.blend')
before_records={n:geometry_record(s.o) for n,s in ss.items()}
mates=dict(plug)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'cleaned/candidate.blend'))
load_collections();assembled();bpy.context.view_layer.update()
current={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
assert set(current)==set(before_records)
changed=sorted(n for n,o in current.items() if geometry_record(o)!=before_records[n]);assert changed==['Pitch_Yoke','Yaw_Base']
ss={n:Solid(o) for n,o in current.items()};obstacles=dict(ss);obstacles.update({'Plug_'+n:s for n,s in mates.items()});trees={n:s.bvh() for n,s in obstacles.items()}
audit_helper=VERIFY_DIR/'repair_threading_storage.py'
exec(compile('def mesh_check'+audit_helper.read_text().split('def mesh_check',1)[1].split('\nrows=[]',1)[0],str(audit_helper),'exec'),globals())
topology=[]
for name in changed:
    stats,solid,v,f=mesh_check(current[name].data)
    expected=np.load(OUT/'cleaned'/f'{name}.npz')
    stats['vertices_match_saved_npz']=bool(np.array_equal(v,expected['vertices_mm']))
    stats['triangles_match_saved_npz']=bool(np.array_equal(f,expected['triangles']))
    assert stats['status']=='PASS' and stats['vertices_match_saved_npz'] and stats['triangles_match_saved_npz']
    topology.append({'part':name,**stats})
print('J3_RELOAD_TOPOLOGY_PASS',flush=True)

motion_helper=VERIFY_DIR/'check_body_prefix_motion.py'
exec(compile('def check_one'+motion_helper.read_text().split('def check_one',1)[1].split('\nfor yaw in yaws:',1)[0],str(motion_helper),'exec'),globals())
routes=np.load(VERIFY_DIR/'body_prefix_v2/body_to_yaw_curves.npz')
motion=json.loads((VERIFY_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
assert motion['curves_sha256']==sha(VERIFY_DIR/'body_prefix_v2/body_to_yaw_curves.npz') and motion['status']=='PASS'
checks=[]
for row in motion['rows']:
    pts=routes[row['array_key']];yaw=row['yaw_deg'];hits=[]
    for name,s in obstacles.items():
        for pitch in (range(-20,26,5) if s.group=='pitch' else [0]):
            if s.group in ['yaw','pitch']:
                inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)));p=pts@inv[:3,:3].T+inv[:3,3]
            else:p=pts
            hit=check_one(p,row['curve_error_bound_mm'],s.lo,s.hi,s.m,trees[name],101 if name=='Plug_motion_J5' else 0)
            if hit:hits.append({'object':name,'pitch_deg':pitch,**hit});break
    for name,s in fixed.items():
        hit=check_one(pts,row['curve_error_bound_mm'],s['lo'],s['hi'],s['m'],s['tree'])
        if hit:hits.append({'object':name,**hit})
    checks.append({'pin':row['pin'],'yaw_deg':yaw,'status':'PASS' if not hits else 'BLOCKED','hits':hits})
print('J3_RUNNING_WIRES',sum(r['status']!='PASS' for r in checks),flush=True)

# Rebuild smaller *required-clearance* envelopes directly from the analytic
# feed poses. They retain >=.3mm nominal clearance and sit inside the larger
# construction cutters. This tests actual reloaded material, not a mesh-distance
# tolerance waiver after cleanup.
feed=json.loads((OUT/'coupled_feed_screen.json').read_text());chosen=next(r for r in feed['tested_cases'] if r['radius_mm']==feed['selected_radius_mm'])
tr=[np.array(t) for t in chosen['cases'][0]['contact_transforms_3x4']]
merge={i:j for i,j in construction['merged_straight_intervals']};intervals=[];i=0
while i<len(tr)-1:
    j=merge.get(i,i+1);intervals.append((i,j));i=j
assert len(intervals)==construction['segments_per_phase']
sp=manifold.Manifold.sphere(.31,32);m=sp.to_mesh64();v=np.array(m.vert_properties[:,:3]);f=np.array(m.tri_verts)
a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]];n=np.cross(b-a,c-a)
inner=float(np.abs(np.einsum('ij,ij->i',a,n)/np.linalg.norm(n,axis=1)).min())
contact_bound=inner-construction['contact_interpolation_error_bound_mm'];assert contact_bound>.3
template=manifold.Manifold.cube([.8,1.35,3.9],center=True).minkowski_sum(sp)
instances=[template.transform(t) for t in tr]
contact_core=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([instances[i],instances[j]]) for i,j in intervals],manifold.OpType.Add)
wire_sp=manifold.Manifold.sphere(.641,32);wire_bound=inner/.31*.641-chosen['curve_chord_error_bound_mm']-.3302;assert wire_bound>.3
p=np.array(chosen['cases'][0]['wire_rear_curve_mm']);q=p.copy();er=np.array([math.sqrt(.5),math.sqrt(.5),0.]);old_end=178+16*math.sin(math.pi/3);new_end=old_end+1
for i,(pt,label) in enumerate(zip(p,chosen['segment_names'])):
    q[i]=pt-.8*er
    if label=='central_straight':q[i,2]=147+(pt[2]-147)*32/31
    elif label.startswith('upper_R8'):q[i,2]=pt[2]+1
    elif label=='upper_free_end':q[i,2]=new_end+(pt[2]-old_end)*(206-new_end)/(202.1-old_end)
tail_core=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([wire_sp.translate(pt.tolist()) for pt in [p[i],p[j],q[i],q[j]]]) for i,j in intervals],manifold.OpType.Add)
core=contact_core+tail_core;feed_checks=[]
for phase in [45,135,225,315]:
    shape=core.rotate((0,0,phase-45));bb=np.array(shape.bounding_box());hits=[]
    for name,s in obstacles.items():
        if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
        volume=max(0.,float((shape^s.m).volume()))
        if volume>1e-6:hits.append({'object':name,'volume_mm3':volume})
    for name,s in fixed.items():
        if np.any(bb[:3]>s['hi']) or np.any(bb[3:]<s['lo']):continue
        volume=max(0.,float((shape^s['m']).volume()))
        if volume>1e-6:hits.append({'object':name,'volume_mm3':volume})
    feed_checks.append({'phase_deg':phase,'status':'PASS' if not hits else 'BLOCKED','hits':hits})
result={'status':'PASS' if all(r['status']=='PASS' for r in checks+feed_checks) else 'BLOCKED',
    'scope':'Reloaded J3 topology,130 nominal installed head poses and continuous loose contact/tail/first reshaping envelopes',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(VERIFY_SCRIPT),'source_helper_sha256':sha(VERIFY_HELPER),
    'source_storage_sha256':sha(OUT/'cleaned/storage.json'),'source_construction_sha256':sha(OUT/'candidate_screen.json'),
    'source_feed_sha256':sha(OUT/'coupled_feed_screen.json'),'source_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),
    'source_mates_sha256':sha(VERIFY_DIR/'amass_mating/received_dimensions.json'),
    'source_wire_curves_sha256':sha(VERIFY_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'source_fixed_wires_sha256':sha(fixed_path),'changed_existing_ids':changed,'unchanged_other_source_parts':207,
    'topology':topology,'installed_wire_checks':checks,'head_pose_count':130,'wire_pose_instances':520,
    'all_source_count':209,'mating_allocation_count':29,'prior_static_wire_count':14,
    'feed_checks':feed_checks,'nominal_contact_gap_bound_mm':contact_bound,'nominal_tail_gap_bound_mm':wire_bound,
    'main_applied':False,'minimum_wall_and_strength':'NOT_TESTED','whole_harness':'BLOCKED',
    'body_loose_tail_placement':'NOT_TESTED','hand_access':'NOT_TESTED','physical_threading':'NOT_TESTED',
    'elapsed_s':time.time()-VERIFY_START}
(OUT/'reloaded_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash and sha(OUT/'cleaned/candidate.blend')==storage['candidate_blend_sha256']
print('J3_RELOAD_COMPLETE',result['status'],contact_bound,wire_bound,round(time.time()-VERIFY_START,2),flush=True)
