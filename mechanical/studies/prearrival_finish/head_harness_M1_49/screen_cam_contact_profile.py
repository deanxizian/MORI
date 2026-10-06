"""Screen a vertical contact rather than forcing its long axis along the bend.

This is a rigid-body path hypothesis, not proof of free-wire feeding or a
supplier contact selection. The reaction link remains an obstacle.
"""
from pathlib import Path
import json, math, sys, time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'contact_profile'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold

ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',BASE/'CAM_PH_RECEIPT.json']
inputs=list(reports)+[HERE/'screen_cam_contact_vertical.py',REST/'contact_vertical/review.json']
for path in reports:
    r=read(path);assert r['status']=='PASS'
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
deferred=set(read(reports[0])['not_yet_installed'])|{'Plug_motion_J5'}
original=ctx.targets;targets={n:t for n,t in original.items() if n not in deferred}
def stored(path):
    inputs.append(path);a=np.load(path)
    return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
for n,p in [('Pitch_Cradle',C/'Pitch_Cradle_candidate.npz'),('Pitch_Yoke',G/'Pitch_Yoke_candidate.npz'),
            ('connector_band',C/'band.npz'),('connector_head',C/'head.npz'),('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz')]:
    targets[n]=ctx.target(stored(p))
path=J/'candidate_curves.npz';inputs.append(path);curves=np.load(path)
base=manifold.Manifold.cube([2.08,1.5,5.7]).translate([-1.04,-.75,0.])
arrays={};rows=[]
full=curves['CAM_1_y0_p0'];guide=np.array([-26.600000143051147,-11.,224.])
i=int(np.argmin(np.linalg.norm(full-guide,axis=1)));assert np.linalg.norm(full[i]-guide)<1e-6
q=full[:i+1][::-1];end=int(np.flatnonzero(q[:,2]<=142.5)[0]);q=q[:end+1]
u=(142.5-q[-2,2])/(q[-1,2]-q[-2,2]);q[-1]=q[-2]+u*(q[-1]-q[-2])
ds=np.linalg.norm(np.diff(q,axis=0),axis=1);s=np.r_[0.,np.cumsum(ds)]
station=np.linspace(0.,s[-1],math.ceil(s[-1]/.1)+1)
reference=np.column_stack([np.interp(station,s,q[:,k]) for k in range(3)])
zknots=np.array([142.5,148.,173.,178.,183.,188.,190.,192.,194.,198.,202.,207.])
rknots=np.array([11.,11.,10.5,10.5,11.5,13.,13.2,13.4,13.6,14.,14.2,14.2])
smooth=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
for offset in [0.,.15,-.15]:
    variant=f'offset{offset:+.2f}';points=reference.copy();radius=np.linalg.norm(points[:,:2],axis=1)
    profile=np.interp(points[:,2],zknots,rknots)+offset
    w=smooth((207.-points[:,2])/5.)
    points[:,:2]*=(1+w*(profile/radius-1))[:,None]
    # Continue below the guide-window bottom so the result can distinguish
    # entering the lower window from actually emerging at its underside.
    last=points[-1].copy();extension=np.linspace(last,last+[0,0,-6.],61);points=np.vstack([points,extension[1:]])
    distances=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    actual_station=np.linspace(0,distances[-1],math.ceil(distances[-1]/.1)+1)
    points=np.column_stack([np.interp(actual_station,distances,points[:,k]) for k in range(3)])
    tangent=np.gradient(points,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    rotations=[];first=None;checked=0
    for n,(p,track_t) in enumerate(zip(points,tangent)):
        blend=float(smooth((204.-p[2])/4.));t=(1-blend)*np.array([0.,0.,-1.])+blend*track_t;t/=np.linalg.norm(t)
        radial=np.r_[p[:2],0.];radial/=np.linalg.norm(radial);desired=np.cross(radial,t);desired/=np.linalg.norm(desired)
        if desired[0]<0:desired=-desired
        initial=np.array([1.,0.,0.]);initial-=t*np.dot(initial,t);initial/=np.linalg.norm(initial)
        roll=float(smooth((221.-p[2])/10.));x=(1-roll)*initial+roll*desired;x-=t*np.dot(x,t);x/=np.linalg.norm(x);y=np.cross(t,x)
        m=base.transform(np.column_stack([x,y,t,p]));box=np.asarray(m.bounding_box());hits=[]
        for name,target in targets.items():
            if not(np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
            overlap=float((m^target['m']).volume());gap=float(m.min_gap(target['m'],.301)) if abs(overlap)<1e-7 else 0.
            if abs(overlap)>1e-6 or gap<.3-1e-5:hits.append(dict(target=name,overlap_mm3=overlap,gap_mm=gap))
        rotations.append(np.column_stack([x,y,t]));checked+=1
        if hits:
            first=dict(index=n,station_mm=float(actual_station[n]),rear_mm=p.tolist(),tangent=t.tolist(),x_axis=x.tolist(),hits=hits)
            a=m.to_mesh64();np.savez_compressed(OUT/f'blocked_{variant}.npz',vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts);break
    arrays[variant+'_points']=points[:checked];arrays[variant+'_rotations']=np.asarray(rotations)
    rows.append(dict(variant=variant,status='BLOCKED' if first else 'PASS',checked_positions=checked,planned_positions=len(points),
        path_length_mm=float(distances[-1]),maximum_position_step_mm=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max()),
        last_rear_z_mm=float(points[checked-1,2]),first_failure=first))
    print('CONTACT_PROFILE',rows[-1],flush=True)
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'paths.npz',**arrays)
report=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Three radial profiles for a free nominal PH contact through the neck; final wire centrelines unchanged; not complete cable feeding',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},rows=rows,
    radial_profile_z_mm=zknots.tolist(),radial_profile_r_mm=rknots.tolist(),radial_offsets_mm=[0,.15,-.15],
    terminal_mm=[2.08,1.5,5.7],not_yet_installed=sorted(deferred),Yaw_Reaction_Link_present=True,
    free_wire_shape='NOT_TESTED',peer_CAM_wires='NOT_TESTED',continuous_sweep='NOT_TESTED',actual_crimped_envelope='BLOCKED',
    full_harness='BLOCKED',main_changed=False,approved=False,C6_main_applied=False,
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CONTACT_PROFILE_DONE',report['status'],report['elapsed_s'],flush=True)
