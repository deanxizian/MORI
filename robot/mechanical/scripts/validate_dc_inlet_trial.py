"""Independent saved-model comparison and local DC trial-seat checks."""
import hashlib
from common import *


def raw(row):
    return manifold.Manifold(manifold.Mesh64(np.array(row['vertices'],dtype=float,order='C'),
        np.array(row['triangles'],dtype=np.uint64,order='C')))


def validate_dc(ss):
    q=P['dc_inlet_trial'];folder=PROJECT/q['baseline'];base=json.loads(folder.read_text());folder=folder.parent
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha(folder/'baseline.json')==q['baseline_sha256']
    for file,digest in base['files'].items():assert sha(folder/file)==digest,file
    actual={o.name.removeprefix(PREFIX):o for o in parts()};errors=[];new=set(q['reference_ids'])
    expected=set(base['parts'])|new
    if set(actual)!=expected:errors.append(dict(kind='inventory',missing=sorted(expected-set(actual)),extra=sorted(set(actual)-expected)))
    same=[];max_pose=0.
    for name,row in base['parts'].items():
        o=actual[name];o.data.calc_loop_triangles()
        vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32)
        ff=np.array([list(t.vertices) for t in o.data.loop_triangles],dtype=np.uint32)
        unchanged=(hashlib.sha256(vv.tobytes()).hexdigest()==row['vertices_sha256'] and
                   hashlib.sha256(ff.tobytes()).hexdigest()==row['triangles_sha256'])
        if name!='Body_Rear' and not unchanged:errors.append(dict(kind='mesh',part=name))
        delta=float(np.max(np.abs(np.array(o.matrix_world)-row['matrix_world'])));max_pose=max(max_pose,delta)
        if delta>2e-5:errors.append(dict(kind='pose',part=name,error=delta))
        if o.get('category')!=row['category'] or o.get('data_status')!=row['data_status']:
            errors.append(dict(kind='evidence_label',part=name))
        if unchanged:same.append(name)
    reference=json.loads((folder/'sample_mount_candidate_meshes.json').read_text());diffs={}
    for name,row in reference.items():
        target='Body_Rear' if name=='Body_Rear_DC_TRIAL' else name
        want=raw(row);m=ss[target].m
        delta=max(0.,float((want-m).volume()))+max(0.,float((m-want).volume()));diffs[target]=delta
        if delta>.01:errors.append(dict(kind='approved_candidate',part=target,difference_mm3=delta))
    for name in new:
        if actual[name]['category']!='PLACEHOLDER' or actual[name]['data_status']!='ASSUMED':errors.append(dict(kind='allocation_label',part=name))
    old=np.load(folder/'body_rear_before.npz');before=raw(dict(vertices=old['vertices'],triangles=old['triangles']))
    shell=ss['Body_Rear'].m;added=shell-before
    parts_m={n:s.m for n,s in ss.items()};bounds_m={n:np.array(m.bounding_box()) for n,m in parts_m.items()}
    def hits(m,targets):
        a=np.array(m.bounding_box());out=[]
        for name in targets:
            b=bounds_m[name]
            if np.any(a[3:]<b[:3]) or np.any(b[3:]<a[:3]):continue
            v=float((m^parts_m[name]).volume())
            if v>.05:out.append(dict(part=name,volume_mm3=v))
        return out
    added_hits=hits(added,set(ss)-{'Body_Rear'}-new)
    accessory_hits={n:hits(ss[n].m,set(ss)-new) for n in new}
    # Independent transform from the frozen reviewed candidate, not builder code.
    review=json.loads((folder/'sample_mount_candidate_check.json').read_text())['parameters']
    tr=Matrix.Translation(Vector(review['flange_plane_origin_mm']))@Vector(review['outward_normal']).to_track_quat('Z','Y').to_matrix().to_4x4()
    tf=lambda m:m.transform(np.asarray(tr,dtype=float)[:3,:])
    cyl=lambda r,a,b,seg=512:manifold.Manifold.cylinder(b-a,r,r,seg,False).translate([0,0,a])
    missing=[]
    for angle in np.linspace(0,2*math.pi,49)[:-1]:
        for radius in [4.2,5.,6.,7.]:
            pin=cyl(.05,-3.99,-.01,16).translate([radius*math.cos(angle),radius*math.sin(angle),0])
            missing.append(max(0.,float((tf(pin)-shell).volume())))
    tool=cyl(8,-40,-6)-cyl(5.1,-41,-5);tool_hits=[]
    for d in np.linspace(0,30,61):
        found=hits(tf(tool.translate([0,0,-float(d)])),{'Body_Rear','DC_Jack_Sample_Allocation'})
        if found:tool_hits.append(dict(travel_mm=float(d),hits=found))
    checks=dict(added_material=dict(status='FAIL' if added_hits else 'PASS',hits=added_hits),
        installed_accessory_capacity=dict(status='FAIL' if any(accessory_hits.values()) else 'PASS',hits=accessory_hits),
        integral_seat=dict(status='PASS' if max(missing)<1e-5 and len(shell.decompose())==1 else 'FAIL',
            sample_count=len(missing),max_missing_mm3=max(missing),nominal_wall_mm=4,connected_solids=len(shell.decompose())),
        loose_shell_tool_capacity=dict(status='FAIL' if tool_hits else 'PASS',samples=61,OD_mm=16,ID_mm=10.2,hits=tool_hits,
            prerequisite='Loose rear shell before interface PCB; tool is an ASSUMED hollow envelope'))
    for name,item in checks.items():
        if item['status']!='PASS':errors.append(dict(kind='local_check',check=name))
    report=dict(revision=P['revision'],status='FAIL' if errors else 'PASS',errors=errors,
        source_blend_sha256=sha(ROOT/'mori.blend'),baseline_revision=base['revision'],baseline_source_sha256=base['source_main_sha256'],
        changed_existing_ids=['Body_Rear'],unchanged_existing_count=len(same),new_reference_ids=sorted(new),
        maximum_pose_error_mm=max_pose,approved_solid_difference_mm3=diffs,checks=checks,
        actual_hole_fit='NOT_TESTED',complete_lead_insertion='BLOCKED',physical_strength='NOT_TESTED',
        scope='Saved mesh equality to approved independent candidate, unchanged remaining parts/poses, 192 seat probes and 61 loose-shell tool poses. Full sample tail is a capacity allocation, not a proven insertable rigid socket.',
        new_prints=0,new_fasteners=0,manufacturing_release=False)
    save_json(ROOT/'reports/dc_inlet_validation.json',report)
    if errors:raise RuntimeError('DC adoption failed: '+str(errors))
    return report
