"""Readback checks against independently frozen approval and M1.57 fingerprints."""
import hashlib
from common import *
from validate_off_shelf_modules import raw_solid


def validate_controls(ss):
    q=P['ups_rear_controls'];folder=PROJECT/q['baseline'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha(folder)==q['baseline_sha256'];base=json.loads(folder.read_text());folder=folder.parent
    for f,h in base['files'].items():assert sha(folder/f)==h,f
    actual={o.name.removeprefix(PREFIX):o for o in parts()};errors=[];removed=set(q['retired_ids']);new=set(q['reference_ids'])
    expected=(set(base['parts'])-removed)|new
    if set(actual)!=expected:errors.append(dict(kind='inventory',missing=sorted(expected-set(actual)),extra=sorted(set(actual)-expected)))
    same=[];maximum_pose=0.
    for n,row in base['parts'].items():
        if n in removed:continue
        o=actual[n];o.data.calc_loop_triangles()
        vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32);ff=np.array([list(t.vertices) for t in o.data.loop_triangles],dtype=np.uint32)
        match=hashlib.sha256(vv.tobytes()).hexdigest()==row['vertices_sha256'] and hashlib.sha256(ff.tobytes()).hexdigest()==row['triangles_sha256']
        if match:same.append(n)
        elif n!='Body_Rear':errors.append(dict(kind='mesh',part=n))
        delta=float(np.max(np.abs(np.array(o.matrix_world)-row['matrix_world'])));maximum_pose=max(maximum_pose,delta)
        if delta>2e-5:errors.append(dict(kind='pose',part=n,error=delta))
        if o.get('category')!=row['category'] or o.get('data_status')!=row['data_status']:errors.append(dict(kind='evidence',part=n))
    diffs={}
    for n,row in json.loads((folder/'candidate_meshes.json').read_text()).items():
        want=raw_solid(row);m=ss[n].m
        delta=max(0.,float((want-m).volume()))+max(0.,float((m-want).volume()));diffs[n]=delta
        if delta>.02:errors.append(dict(kind='approved_solid',part=n,delta_mm3=delta))
    for n in new:
        if actual[n]['category']!='PLACEHOLDER' or actual[n]['data_status']!='ASSUMED':errors.append(dict(kind='sample_label',part=n))
    shell=ss['Body_Rear'].m;old=np.load(folder/'body_rear_before.npz');before=raw_solid(dict(vertices=old['vertices'],triangles=old['triangles']))
    solids={n:s.m for n,s in ss.items()};bbs={n:np.array(m.bounding_box()) for n,m in solids.items()}
    def hits(m,names,tol=.01):
        a=np.array(m.bounding_box());out=[]
        for n in names:
            b=bbs[n]
            if np.any(a[3:]<b[:3]) or np.any(b[3:]<a[:3]):continue
            v=float((m^solids[n]).volume())
            if v>tol:out.append(dict(part=n,volume_mm3=v))
        return out
    checks={};changed={'Body_Rear'}|new
    hh=hits(shell-before,set(ss)-changed);checks['added_material']=dict(status='FAIL' if hh else 'PASS',hits=hh)
    hh={n:hits(solids[n],set(ss)-{n}) for n in new};checks['installed_switch']=dict(status='FAIL' if any(hh.values()) else 'PASS',hits=hh)
    frozen=json.loads((folder/'candidate_check.json').read_text())['parameters']
    switch_tr=Matrix(frozen['switch_matrix_world'])
    dc_review=json.loads((PROJECT/P['dc_inlet_trial']['baseline']).parent.joinpath('sample_mount_candidate_check.json').read_text())['parameters']
    dc_tr=Matrix.Translation(Vector(dc_review['flange_plane_origin_mm']))@Vector(dc_review['outward_normal']).to_track_quat('Z','Y').to_matrix().to_4x4()
    cyl=lambda r,a,b,seg=1024:manifold.Manifold.cylinder(b-a,r,r,seg,False).translate([0,0,a])
    for key,tr,radii,OD,ID,jack,nut in [
        ('switch',switch_tr,[6.2,7,8,9.4],18,12.2,'UPS_Switch_Sample_Allocation','UPS_Switch_Nut_Sample_Allocation'),
        ('DC',dc_tr,[4.2,5,6,7],16,10.2,'DC_Jack_Sample_Allocation','DC_Nut_Sample_Allocation')]:
        tf=lambda m:m.transform(np.asarray(tr,dtype=float)[:3,:]);missing=[]
        for a in np.linspace(0,2*math.pi,49)[:-1]:
            for r in radii:missing.append(max(0.,float((tf(cyl(.04,-3.99,-.01,16).translate([r*math.cos(a),r*math.sin(a),0]))-shell).volume())))
        checks[key+'_material']=dict(status='PASS' if max(missing)<1e-5 else 'FAIL',samples=len(missing),max_missing_mm3=max(missing))
        tool=cyl(OD/2,-40,-6)-cyl(ID/2,-41,-5);bad=[]
        bench={'Body_Rear',*new,*P['dc_inlet_trial']['reference_ids']}-{nut}
        for d in np.linspace(0,30,61):
            h=hits(tf(tool.translate([0,0,-float(d)])),bench)
            if h:bad.append(dict(travel_mm=float(d),hits=h))
        checks[key+'_nut_tool']=dict(status='FAIL' if bad else 'PASS',samples=61,hits=bad,OD_mm=OD,ID_mm=ID,prerequisite='Loose rear shell; hollow tool capacity, not measured tool')
    # Compare the entire approved DC mount vicinity to the immutable prior shell.
    zone=cyl(8,-6,2).transform(np.asarray(dc_tr,dtype=float)[:3,:]);dv=max(0.,float(((shell-before)^zone).volume()))+max(0.,float(((before-shell)^zone).volume()))
    checks['DC_seat_preserved']=dict(status='PASS' if dv<.02 else 'FAIL',difference_mm3=dv)
    checks['topology']=dict(status='PASS' if len(shell.decompose())==1 else 'FAIL',connected_solids=len(shell.decompose()))
    # Changes outside the exact approved fill, ledge and switch seat/cut zones.
    box=lambda b:manifold.Manifold.cube((np.array(b[1])-b[0]).tolist()).translate(b[0])
    allowed=box(q['legacy_usb_fill_bounds_mm'])
    for b in q['retired_ledge_bounds_mm']:allowed+=box(b)
    allowed+=cyl(10,-4,20).transform(np.asarray(switch_tr,dtype=float)[:3,:]);allowed+=cyl(6,-40,20).transform(np.asarray(switch_tr,dtype=float)[:3,:])
    dv=max(0.,float(((shell-before)-allowed).volume()))+max(0.,float(((before-shell)-allowed).volume()))
    checks['local_scope']=dict(status='PASS' if dv<.02 else 'FAIL',outside_declared_zones_delta_mm3=dv)
    for n,c in checks.items():
        if c['status']!='PASS':errors.append(dict(kind='local_check',check=n))
    video={f:sha(PROJECT/f)==h for f,h in base['protected_video'].items()}
    if not all(video.values()):errors.append(dict(kind='unrequested_animation_change'))
    report=dict(revision=P['revision'],status='FAIL' if errors else 'PASS',errors=errors,source_blend_sha256=sha(ROOT/'mori_v1_2.blend'),baseline_revision=base['revision'],baseline_main_sha256=base['source_main_sha256'],changed_existing_ids=['Body_Rear'],unchanged_existing_count=len(same),retired_ids=sorted(removed),new_reference_ids=sorted(new),maximum_pose_error_mm=maximum_pose,approved_solid_difference_mm3=diffs,checks=checks,animation_unchanged=video,custom_PCB_ids=['MCU_Carrier'],carrier_geometry='Retained P5R7 reference; new UPS-R1 electrical board not designed/frozen',new_prints=0,physical_fit='NOT_TESTED',complete_lead_insertion='BLOCKED',physical_strength='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/ups_controls_validation.json',report)
    if errors:raise RuntimeError('UPS controls adoption failed: '+str(errors))
    return report
