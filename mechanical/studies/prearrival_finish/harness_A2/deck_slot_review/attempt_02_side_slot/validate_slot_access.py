# -*- coding: utf-8 -*-
"""Closed deck slot / bare PHR8 feed candidate. Main assembly is read-only."""
from pathlib import Path
import json,hashlib,sys,time,itertools
STAGE=Path(__file__).resolve().parent
code=(STAGE/'check_static.py').read_text().split('specs=[')[0]
exec(compile(code,str(STAGE/'check_static.py'),'exec'),globals())
sys.path.insert(0,str(STAGE))
from deck_slot_candidate import apply_to_study
before=ss['Load_Frame'].m
candidate=apply_to_study(globals());after=ss['Load_Frame'].m
removed=before-after
outdir=STAGE/'deck_slot_review';outdir.mkdir(exist_ok=True)
start=time.time()

def poly_gap(A,B):
    A=np.array(A);B=np.array(B)
    # Disjoint planar contours: the minimum of segment pairs is attained by
    # an endpoint-to-segment distance. Both directions are evaluated.
    results=[]
    for pts,ends in [(A,B),(B,A)]:
        vec=np.roll(ends,-1,axis=0)-ends
        w=pts[:,None,:]-ends[None,:,:]
        t=np.clip(np.sum(w*vec[None,:,:],axis=2)/np.maximum(np.sum(vec*vec,axis=1),1e-15),0,1)
        results.append(float(np.min(np.linalg.norm(w-t[:,:,None]*vec[None,:,:],axis=2))))
    return min(results)

sections=[]
for z in [111.01,111.5,112.,112.5,113.,113.5,114.,114.5,114.99]:
    contours=[np.asarray(p) for p in after.slice(z).to_polygons()]
    slot_ids=[i for i,p in enumerate(contours) if np.max(abs(p[:,0]-40))<3.501 and np.max(abs(p[:,1]+37))<11.001 and len(p)>20]
    assert len(slot_ids)==1,(z,slot_ids)
    idx=slot_ids[0]
    gaps=[dict(contour=i,gap_mm=poly_gap(contours[idx],p),bounds_xy_mm=[p.min(0).tolist(),p.max(0).tolist()]) for i,p in enumerate(contours) if i!=idx]
    sections.append(dict(z_mm=z,slot_contour=contours[idx].tolist(),minimum=min(gaps,key=lambda r:r['gap_mm']),other_contours=gaps))

touches=[];hardware_gaps=[]
for n,s in obstacles.items():
    if n=='Load_Frame':continue
    bb=s.m.bounding_box();rr=removed.bounding_box()
    if any(bb[i]>rr[i+3]+5 or rr[i]>bb[i+3]+5 for i in range(3)):continue
    overlap=max(0,(removed^s.m).volume())
    if overlap>.0001:touches.append(dict(object=n,volume_mm3=overlap))
    if n.startswith(('Frame_Screw','Frame_Insert','Carrier_','IMU_')):
        hardware_gaps.append(dict(object=n,gap_to_removed_region_mm=removed.min_gap(s.m,10.)))

upper=set(json.loads((PROJECT/'mechanical/reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']['moving'])
bridge={'Yaw_Base','Yaw_Bearing'}|{n for n in ss if n.startswith(('Yaw_Base_-1_Nut','Yaw_Base_1_Nut','Yaw_Keeper_Insert_'))}
omitted=upper|bridge|{n for n,s in ss.items() if s.group in ['pitch','yaw']}
fixed={n:s.m for n,s in ss.items() if n not in omitted}
fixed.update({'Plug_'+k:p.m for k,p in plug.items() if k not in ['imu_J1','rear_J2','rear_J3']})
target=plug['imu_J1'];center=(target.lo+target.hi)/2
def pose(c,angle):
    return Matrix.Translation(Vector(c))@Matrix.Rotation(math.radians(angle),4,'Z')@Matrix.Translation(Vector(-center))
stages=[('feed_vertical_before_shell_bridge',[(np.array([40.,-37.,z]),90.) for z in np.arange(134.,93.99,-.5)]),
    ('move_rear_before_turn',[(np.array([40.,y,94.]),90.) for y in np.linspace(-37,-44,29)]),
    ('translate_inward',[(np.array([x,-44.,94.]),90.) for x in np.linspace(40,20,81)]),
    ('turn_under_deck',[(np.array([20.,-44.,94.]),a) for a in np.linspace(90,0,61)]),
    ('approach_IMU_below',[(np.array([x,-44.,94.]),0.) for x in np.linspace(20,-25,181)])]
paths=[]
for label,steps in stages:
    hits=[]
    for i,(c,ang) in enumerate(steps):
        m=target.m.transform(np.asarray(pose(c,ang))[:3,:]);bb=m.bounding_box()
        for n,other in fixed.items():
            ob=other.bounding_box()
            if any(bb[k+3]<=ob[k] or ob[k+3]<=bb[k] for k in range(3)):continue
            v=max(0,(m^other).volume())
            if v>.001:hits.append(dict(sample=i,part=n,overlap_mm3=v))
    paths.append(dict(id=label,status='PASS' if not hits else 'FAIL',samples=len(steps),hits=hits))
    print('SLOT_FEED',label,paths[-1]['status'],len(hits),flush=True)
result=dict(source_blend_sha256=source_hash,candidate=candidate,
    status='PASS' if not touches and all(r['status']=='PASS' for r in paths) and min(s['minimum']['gap_mm'] for s in sections)>=1.5 else 'FAIL',
    scope='Local slot material and bare housing path up to below IMU; not attached-wire feeding or final terminal insertion',
    structural=dict(removed_mm3=removed.volume(),added_mm3=max(0,(after-before).volume()),
        connected_components=len(after.decompose()),intersections_with_other_parts=touches,
        minimum_sampled_planar_land_mm=min(s['minimum']['gap_mm'] for s in sections),sections=sections,
        nearby_hardware_gaps=hardware_gaps),
    bare_housing_paths=paths,samples=sum(r['samples'] for r in paths),
    assembly_prerequisites=dict(removed_objects=sorted(omitted),upper_shell_bridge_head_absent=True,battery_tray_retained=True),
    elapsed_s=time.time()-start,main_geometry_changed=False,adopted=False,
    limits=['Slot is an unadopted local structural proposal; PA12 strength and edge treatment unqualified.',
        'Bare nominal PHR8 housing only: cable-attached feeding, hand grip, terminal insertion and service loop NOT_TESTED.',
        'Finite discrete rigid positions only, not tolerance or continuous motion proof.',
        'Other boards, fasteners, pack/tray and stored mating envelopes remain obstacles.'])
(outdir/'slot_access.json').write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('SLOT_ACCESS',result['status'],result['structural']['minimum_sampled_planar_land_mm'],result['samples'],time.time()-start,flush=True)
