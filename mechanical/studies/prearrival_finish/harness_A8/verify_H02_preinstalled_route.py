"""Check the saved H02 candidate against solids, all other body wires and stages.

This does not qualify unknown connector exits, flexible cable installation,
supplier cutting lengths, continuous joint motion or physical assembly.
"""
from pathlib import Path
VERIFY=Path(__file__).resolve();SCRIPT_A8=VERIFY.parent
BOOT=SCRIPT_A8/'screen_H02_preinstalled_route.py'
__file__=str(BOOT)
exec(compile(BOOT.read_text().split('\nstarted=time.time();pools=',1)[0],str(BOOT),'exec'),globals())
__file__=str(VERIFY)
from interface_completion import axial
from validate import rigidtr
screen_path=OUT/'screen.json';saved=json.loads(screen_path.read_text())
assert saved['status']=='PASS' and saved['script_sha256']==sha(BOOT)
selected=saved['selected']['routes'];assert len(selected)==2
started=time.time();solids={};geometries={};solid_rows=[]
unit=manifold.Manifold.sphere(1.,32).to_mesh64();uv=np.asarray(unit.vert_properties[:,:3]);uf=np.asarray(unit.tri_verts)
norm=np.cross(uv[uf[:,1]]-uv[uf[:,0]],uv[uf[:,2]]-uv[uf[:,0]])
inradius=float(np.min(np.abs(np.sum(norm*uv[uf[:,0]],axis=1))/np.linalg.norm(norm,axis=1)))
for r in selected:
    points=np.array(r['curve_mm']);cp=np.array(r['controls_mm']);radius=HOD/2+.02
    sag=0.
    for a,b,c in zip(cp,cp[1:],cp[2:]):
        u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
        theta=math.acos(np.clip(u@v,-1,1));steps=max(3,int(R*theta/.5)+1)-1
        sag=max(sag,R*(1-math.cos(theta/(2*steps))))
    facet=radius*(1-inradius)
    assert sag+facet<.02 and sag<=SAG
    pieces=[]
    for a,b in zip(points,points[1:]):
        d=b-a;length=float(np.linalg.norm(d))
        if length>1e-8:pieces.append(axial(radius,length,(a+b)/2,d/length))
    pieces.extend(manifold.Manifold.sphere(radius,32).translate(p) for p in points[1:-1])
    m=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    components=sum(p.volume()>1e-6 for p in m.decompose())
    assert m.status()==manifold.Error.NoError and components==1
    name=r['id'];solids[name]=m;mesh=m.to_mesh64()
    geometries[name]=dict(vertices_mm=mesh.vert_properties[:,:3].tolist(),triangles=mesh.tri_verts.tolist())
    solid_rows.append(dict(id=name,status='PASS',connected_components=components,sag_bound_mm=sag,
                           faceting_bound_mm=facet,radial_inflation_mm=.02))
(OUT/'wire_solids.json').write_text(json.dumps(geometries)+'\n')

def overlaps(shape,targets):
    box=np.array(shape.bounding_box());hits=[]
    for n,(m,lo,hi,tree) in targets.items():
        if np.any(box[:3]>=hi) or np.any(box[3:]<=lo):continue
        volume=max(0.,float((shape^m).volume()))
        if volume>1e-5:hits.append(dict(object=n,intersection_mm3=volume))
    return hits

static_rows=[]
for row in selected:
    p=resample(row['curve_mm'],.04)
    gap=check_curve(p,static,row['from_port'],row['to_port'],rad=HOD/2+.02,extra=0.)
    hits=overlaps(solids[row['id']],static)
    static_rows.append(dict(id=row['id'],status='PASS' if not hits and not gap else 'FAIL',overlaps=hits,clearance_failure=gap))
    print('H02_VERIFY_STATIC',row['id'],static_rows[-1]['status'],hits,gap,flush=True)
segment_code=(A2/'select_joint.py').read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(segment_code,globals())
pair_distance,indices=exact_segment_min(selected[0]['curve_mm'],selected[1]['curve_mm'])
pair_gap=pair_distance-HOD-.04-.0001
pair_volume=max(0.,float((solids['H02_1']^solids['H02_2']).volume()))
pair_row=dict(status='PASS' if pair_gap>=.3 and pair_volume<1e-5 else 'FAIL',
    polyline_distance_mm=pair_distance,inflated_capsule_gap_lower_bound_mm=pair_gap,intersection_mm3=pair_volume)

stages=[
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
deferred={'H01','H04'}
absent={'fixed_wire_'+n for n in fixed if n.split('_')[0] in deferred}|{'Plug_'+p for g in deferred for p in pairings[g]}
target_data={n:d for n,d in all_targets.items() if n not in absent}
target_data.update({'fixed_wire_'+n:data(m) for n,m in solids.items()})
upper_original={n:data(m) for n,m in phys.items() if n in upper}
upper_original.update({'Plug_'+n:data(s.m) for n,s in plug.items() if n.startswith('rear_')})
bridge_original={n:data(phys[n]) for n in bridge}
cam_ph_data={'moving_CAM_PH':data(housing)}
stage_rows=[]
for stage,poses in stages:
    fail=None;checked=0
    for i,(st,bt) in enumerate(poses):
        matrices={'core':bt,'upper':np.linalg.inv(st)@bt,'bridge':I}
        fail=rigid_check(housing,matrices,True)
        if not fail:
            for pin,p in wire.items():
                fail=wire_check(pin,p,matrices) or rigid_check(terminals[pin],matrices)
                if fail:break
        if not fail:
            for row in selected:
                p=resample(row['curve_mm'],.04)
                for label,tr,targets in [('upper',st,upper_original),('bridge',bt,bridge_original),('CAM_PH',bt,cam_ph_data)]:
                    q=transform_points(p,np.linalg.inv(tr))
                    fail=check_curve(q,targets,rad=HOD/2+.02,extra=0.)
                    if fail:fail.update(wire=row['id'],moving_group=label);break
                if fail:break
        checked+=1
        if fail:fail.update(index=i,shell_transform=st.tolist(),bridge_transform=bt.tolist());break
    stage_rows.append(dict(stage=stage,status='PASS' if fail is None else 'FAIL',checked_positions=checked,planned_positions=len(poses),failure=fail))
    print('H02_VERIFY_BODY',stage,stage_rows[-1]['status'],checked,round(time.time()-started,2),flush=True)

head_failures=[];moving={n:s for n,s in ss.items() if s.group in ['yaw','pitch']}
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        for n,s in moving.items():
            tr=np.array(rigidtr(yaw,pitch if s.group=='pitch' else 0))
            m=phys[n].transform(tr[:3,:4]);box=np.array(m.bounding_box())
            for wid,w in solids.items():
                b=np.array(w.bounding_box())
                if np.any(b[:3]>=box[3:]) or np.any(b[3:]<=box[:3]):continue
                volume=max(0.,float((w^m).volume()))
                if volume>1e-5:head_failures.append(dict(wire=wid,object=n,yaw=yaw,pitch=pitch,intersection_mm3=volume))
print('H02_VERIFY_HEAD',len(head_failures),'overlaps',flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in static_rows+stage_rows+[pair_row]) and not head_failures else 'FAIL',
    scope='Two static H02 curves, saved geometry and finite body/head positions only',script_sha256=sha(VERIFY),
    screen_sha256=sha(screen_path),wire_solids_sha256=sha(OUT/'wire_solids.json'),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [BOOT,A2/'ecowire_joint.json',fixed_path,STOCK_OUT/'full_wires.npz']},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209,static_mating_allocations=len(plug),other_fixed_body_wire_count=12,
    solids=solid_rows,static=static_rows,pair=pair_row,body_stages=stage_rows,
    body_source_objects=122,body_installed_harnesses=['H02','H03'],body_deferred_harnesses=['H01','H04'],
    head_poses=130,head_solid_intersections=head_failures,
    terminal_and_wire_selection='ASSUMED_NOT_SELECTED',body_continuous_motion='NOT_TESTED',
    installing_H02_on_open_deck='NOT_TESTED',H01_H04_attached_installation='NOT_TESTED',
    later_yaw_stock='NOT_TESTED',source_routing_lengths_not_supplier_cut_lengths=True,
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('H02_VERIFY_DONE',report['status'],round(time.time()-started,2),flush=True)
