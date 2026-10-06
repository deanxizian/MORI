"""Rotate the existing static throat probe around the unchanged yaw axis.

Finite source-solid screening. Passing would only qualify fixed occupancy of
this nominal planning diameter, not a moving harness or usable anchor.
"""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(BASE.read_text().split('# Endpoints are named')[0],str(BASE),'exec'),globals())
seed_path=HERE/'outer_neck_turn.json';seed=json.loads(seed_path.read_text())
assert seed['source_blend_sha256']==before
row=seed['selected'][0];points=np.asarray(row['curve_mm']);controls=np.asarray(row['cubic_controls_mm'])
diameter=row['probe_diameter_mm'];radius=diameter/2;gap=.3
second=6*np.array([controls[2]-2*controls[1]+controls[0],controls[3]-2*controls[2]+controls[1]])
curve_error=float(np.linalg.norm(second,axis=1).max()/((len(points)-1)**2*8))
clear=radius+gap+row['maximum_chord_mm']/2+curve_error+1e-4
trees={n:s.bvh() for n,s in ss.items()}
posed=[(y,p,np.linalg.inv(np.asarray(rigidtr(y,p))),np.linalg.inv(np.asarray(rigidtr(y,0))))
       for y in range(-60,61,10) for p in range(-20,26,5)]

def sample_screen(points,names):
    for name in names:
        s=ss[name]
        mask=np.all(points>=s.lo-clear,axis=1)&np.all(points<=s.hi+clear,axis=1)
        for point in points[mask]:
            dd=trees[name].find_nearest(Vector(point))[3]
            if dd<clear:return dict(object=name,point_in_object_zero_frame_mm=point.tolist(),distance_mm=dd)
        if np.all(points>=s.lo) and np.all(points<=s.hi):
            probe=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (probe^s.m).volume()>probe.volume()*.5:return dict(object=name,inside=True)
    return None

all_names=list(ss);moving={g:[n for n,s in ss.items() if s.group==g] for g in ['yaw','pitch']}
for g in moving: moving[g].sort(key=lambda n:0 if n in ['Head_Rear','Head_Front','Head_Lower_Guard'] else 1)
cases=[];survivors=[]
for angle in range(0,360,5):
    theta=math.radians(angle);rot=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
    pp=points@rot.T
    static_hit=sample_screen(pp,all_names);motion_hit=None
    if not static_hit:
        for y,p,ip,iy in posed:
            for group,inv in [('pitch',ip),('yaw',iy)]:
                local=pp@inv[:3,:3].T+inv[:3,3]
                hit=sample_screen(local,moving[group])
                if hit:motion_hit=dict(yaw_deg=y,pitch_deg=p,**hit);break
            if motion_hit:break
    if not static_hit and not motion_hit:survivors.append(angle)
    cases.append(dict(azimuth_from_rear_deg=angle,static_hit=static_hit,motion_hit=motion_hit,
        sample_screen='PASS' if not static_hit and not motion_hit else 'FAIL'))
print('NECK_AZIMUTH_SCREEN',len(cases),survivors,time.time()-start,flush=True)

checks=[]
if survivors:
    unit=manifold.Manifold.sphere(1,32);mesh=unit.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);t=v[np.asarray(mesh.tri_verts)]
    normals=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
    inradius=float(np.min(np.abs(np.sum(normals*t[:,0],axis=1))))
    inflated=radius+gap+curve_error+1e-4
    pieces=[unit.scale([inflated/inradius]*3).translate(p.tolist()) for p in points]
    for a,b in zip(points,points[1:]):
        delta=b-a;length=np.linalg.norm(delta)
        pieces.append(axial(inflated/math.cos(math.pi/64),length,(a+b)/2,delta/length,segments=64))
    prototype=manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add)
    for angle in survivors:
        m=prototype.rotate([0,0,angle]);bb=np.asarray(m.bounding_box());hits=[];motion=[]
        for name,s in ss.items():
            if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo):continue
            volume=max(0.,(m^s.m).volume())
            if volume>.001:hits.append(dict(object=name,volume_mm3=volume))
        for y,p,_,_ in posed:
            for name,s in ss.items():
                if s.group not in ['pitch','yaw']:continue
                other=s.m.transform(np.asarray(rigidtr(y,p if s.group=='pitch' else 0))[:3,:]);ob=np.asarray(other.bounding_box())
                if np.any(bb[:3]>ob[3:]) or np.any(bb[3:]<ob[:3]):continue
                volume=max(0.,(m^other).volume())
                if volume>.001:motion.append(dict(object=name,yaw_deg=y,pitch_deg=p,volume_mm3=volume))
        checks.append(dict(azimuth_from_rear_deg=angle,static_status='FAIL' if hits else 'PASS',
            fixed_occupancy_130_pose_status='FAIL' if motion else 'PASS',static_hits=hits,motion_hits=motion))
        print('NECK_AZIMUTH_SOLID',angle,len(hits),len(motion),flush=True)

out=dict(status='PASS' if checks and any(c['static_status']=='PASS' and c['fixed_occupancy_130_pose_status']=='PASS' for c in checks) else 'BLOCKED',
    revision=P['revision'],source_blend_sha256=before,seed_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
    seed_file=str(seed_path.relative_to(PROJECT)),angle_step_deg=5,planning_diameter_mm=diameter,
    project_gap_per_side_mm=gap,sample_clearance_with_coverage_mm=clear,curve_error_bound_mm=curve_error,
    cases=cases,closed_solid_checks=checks,elapsed_s=time.time()-start,main_geometry_changed=False,
    scope='Fixed lower-throat occupancy only; no complete or moving harness',
    source_classification='ASSUMED planning diameter and endpoints; saved robot source geometry',
    actual_harness='NOT_TESTED',anchors='NOT_TESTED',installation_path='NOT_TESTED',
    limits=['Finite angle grid and 130 head poses are not continuous-motion proof.',
        'All endpoints and diameters are unselected study allocations.',
        'One fixed occupancy result neither certifies nor rules out a moving cable.',
        'A failed finite family does not prove every possible route is blocked.'])
(HERE/'neck_azimuths.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('NECK_AZIMUTHS_COMPLETE',out['status'],time.time()-start,flush=True)
