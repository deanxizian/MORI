"""Screen a rigid nominal PH contact along each stored final wire centreline.

This is deliberately a restricted path screen, not a complete feeding proof.
Peer CAM wires are omitted here to distinguish a native-geometry obstruction
from the already observed assembly-order conflict above the guide.
"""
from pathlib import Path
import json, math, sys, time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'contact_corridor_inward'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold

ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',BASE/'CAM_PH_RECEIPT.json',REST/'contact_corridor/review.json']
inputs=list(reports)
for path in reports:
    r=read(path);assert r['status'] in ['PASS','BLOCKED']
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
arrays={};rows=[];witnesses=[]
for pin,target_radius in [(p,r) for p in range(1,5) for r in [10.5,10.8,11.1]]:
    variant=f'pin{pin}_r{target_radius}'
    full=curves[f'CAM_{pin}_y0_p0'];guide=np.array([-25.600000143051147-pin,-11.,224.])
    i=int(np.argmin(np.linalg.norm(full-guide,axis=1)));assert np.linalg.norm(full[i]-guide)<1e-6
    q=full[:i+1][::-1];ds=np.linalg.norm(np.diff(q,axis=0),axis=1);s=np.r_[0.,np.cumsum(ds)]
    # Leave the final 10 mm next to the mated connector outside this screen.
    # The PH contact is to be inserted into its housing after passing the neck.
    station=np.linspace(0.,s[-1]-10.,math.ceil((s[-1]-10.)/.25)+1)
    pts=np.column_stack([np.interp(station,s,q[:,k]) for k in range(3)])
    # Smoothly bring the terminal into the middle of the existing annular
    # channel; this does not move or adopt any final wire route.
    smooth=lambda a: np.clip(a,0,1)**2*(3-2*np.clip(a,0,1))
    weight=smooth((207.-pts[:,2])/20.)*smooth((pts[:,2]-135.)/12.)
    radial=np.linalg.norm(pts[:,:2],axis=1)
    pts[:,:2]*=(1+weight*(target_radius/radial-1))[:,None]
    tangent=np.gradient(pts,axis=0);tang=tangent/np.linalg.norm(tangent,axis=1)[:,None]
    sampled_max_step=float(np.linalg.norm(np.diff(pts,axis=0),axis=1).max())
    x=np.array([1.,0.,0.]);prev=tang[0];first=None;checked=0
    for n,(p,t) in enumerate(zip(pts,tang)):
        if n:
            v=np.cross(prev,t);sn=np.linalg.norm(v);cs=np.dot(prev,t)
            if sn>1e-12:
                k=v/sn;x=x*cs+np.cross(k,x)*sn+k*np.dot(k,x)*(1-cs)
        x=x-t*np.dot(x,t);x/=np.linalg.norm(x);prev=t
        radial3=np.r_[p[:2],0.];radial3/=np.linalg.norm(radial3)
        desired=np.cross(t,radial3)
        if np.linalg.norm(desired)>1e-8:
            desired/=np.linalg.norm(desired)
            if np.dot(desired,x)<0:desired=-desired
            angle=math.atan2(np.dot(np.cross(x,desired),t),np.dot(x,desired))
            roll=float(smooth((207.-p[2])/20.))*angle
            xx=x*math.cos(roll)+np.cross(t,x)*math.sin(roll)
        else:xx=x.copy()
        y=np.cross(t,xx)
        m=base.transform(np.column_stack([xx,y,t,p]));box=np.asarray(m.bounding_box());hits=[]
        for name,target in targets.items():
            if not (np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
            overlap=float((m^target['m']).volume())
            gap=float(m.min_gap(target['m'],.301)) if abs(overlap)<1e-7 else 0.
            if abs(overlap)>1e-6 or gap<.3-1e-5:hits.append(dict(target=name,overlap_mm3=overlap,gap_mm=gap))
        checked+=1
        if hits:
            first=dict(index=n,station_mm=float(station[n]),rear_mm=p.tolist(),tangent=t.tolist(),x_axis=xx.tolist(),hits=hits)
            a=m.to_mesh64();np.savez_compressed(OUT/f'blocked_contact_{variant}.npz',vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
            arrays[variant+'_screened']=pts[:n+1];witnesses.append(dict(pin=pin,target_radius_mm=target_radius,**first));break
    if first is None:arrays[variant+'_screened']=pts
    rows.append(dict(pin=pin,target_radius_mm=target_radius,maximum_sampled_position_step_mm=sampled_max_step,status='BLOCKED' if first else 'PASS',checked_positions=checked,planned_positions=len(pts),
        screened_feed_distance_mm=float(station[checked-1]),first_failure=first))
    print('CONTACT_CORRIDOR_INWARD_PIN',pin,rows[-1],flush=True)
np.savez_compressed(OUT/'paths.npz',**arrays)
ctx.targets=original;ctx.assert_unchanged()
r=dict(status='PASS' if all(any(x['status']=='PASS' and x['pin']==p for x in rows) for p in range(1,5)) else 'BLOCKED',
    scope='Restricted inward threading paths with tangential wide contact orientation; final wires and main unchanged; no complete free-wire or peer check',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},
    rows=rows,terminal_oriented_start_xyz_mm=[2.08,1.5,5.7],source_station_step_mm=.25,
    contact_frame='Parallel transport above neck, blended to wide direction tangential to the annular channel below Z187; no supplier clocking adopted',
    peer_CAM_wire_check='NOT_TESTED',free_wire_shape='NOT_TESTED',continuous_sweep='NOT_TESTED',
    actual_crimped_envelope='BLOCKED',full_harness='BLOCKED',main_changed=False,approved=False,C6_main_applied=False,
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CONTACT_CORRIDOR_INWARD_DONE',r['status'],r['elapsed_s'],flush=True)
