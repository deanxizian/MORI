"""Screen a vertical contact rather than forcing its long axis along the bend.

This is a rigid-body path hypothesis, not proof of free-wire feeding or a
supplier contact selection. The reaction link remains an obstacle.
"""
from pathlib import Path
import json, math, sys, time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'contact_vertical'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold

ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',BASE/'CAM_PH_RECEIPT.json']
inputs=list(reports)
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
arrays={};rows=[];witnesses=[]
for variant,pin in [(name,1) for name in ['vertical_X','vertical_Y','vertical_tangential']]:
    full=curves[f'CAM_{pin}_y0_p0'];guide=np.array([-25.600000143051147-pin,-11.,224.])
    i=int(np.argmin(np.linalg.norm(full-guide,axis=1)));assert np.linalg.norm(full[i]-guide)<1e-6
    q=full[:i+1][::-1];ds=np.linalg.norm(np.diff(q,axis=0),axis=1);s=np.r_[0.,np.cumsum(ds)]
    # Leave the final 10 mm next to the mated connector outside this screen.
    # The PH contact is to be inserted into its housing after passing the neck.
    station=np.linspace(0.,s[-1]-10.,math.ceil((s[-1]-10.)/.25)+1)
    pts=np.column_stack([np.interp(station,s,q[:,k]) for k in range(3)])
    first=None;checked=0
    for n,p in enumerate(pts):
        t=np.array([0.,0.,-1.])
        weight=float(np.clip((221.-p[2])/10.,0.,1.));weight=weight*weight*(3-2*weight)
        if variant=='vertical_X':angle=0.
        elif variant=='vertical_Y':angle=weight*math.pi/2
        else:
            desired=math.atan2(p[0],-p[1])
            while desired>math.pi/2:desired-=math.pi
            while desired< -math.pi/2:desired+=math.pi
            angle=weight*desired
        x=np.array([math.cos(angle),math.sin(angle),0.]);y=np.cross(t,x)
        m=base.transform(np.column_stack([x,y,t,p]));box=np.asarray(m.bounding_box());hits=[]
        for name,target in targets.items():
            if not (np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
            overlap=float((m^target['m']).volume())
            gap=float(m.min_gap(target['m'],.301)) if abs(overlap)<1e-7 else 0.
            if abs(overlap)>1e-6 or gap<.3-1e-5:hits.append(dict(target=name,overlap_mm3=overlap,gap_mm=gap))
        checked+=1
        if hits:
            first=dict(index=n,station_mm=float(station[n]),rear_mm=p.tolist(),tangent=t.tolist(),x_axis=x.tolist(),hits=hits)
            a=m.to_mesh64();np.savez_compressed(OUT/f'blocked_contact_{variant}.npz',vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
            arrays[variant+'_screened']=pts[:n+1];witnesses.append(dict(pin=pin,variant=variant,**first));break
    if first is None:arrays[variant+'_screened']=pts
    rows.append(dict(pin=pin,variant=variant,status='BLOCKED' if first else 'PASS',checked_positions=checked,planned_positions=len(pts),
        screened_feed_distance_mm=float(station[checked-1]),first_failure=first))
    print('CONTACT_VERTICAL',variant,rows[-1],flush=True)
np.savez_compressed(OUT/'paths.npz',**arrays)
ctx.targets=original;ctx.assert_unchanged()
r=dict(Yaw_Reaction_Link_present='Yaw_Reaction_Link' in targets,not_yet_installed=sorted(deferred),status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',
    scope='Nominal contact kept vertical along the complete pin1 reference route; three transverse roll choices; peer wires and free-wire shape omitted. A passing route is a rigid contact candidate, not a full feed.',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},
    rows=rows,terminal_oriented_start_xyz_mm=[2.08,1.5,5.7],maximum_position_step_mm=.25,
    contact_frame='Tip remains -Z; X starts +X. Optional roll blends from0atZ221 to90deg or horizontal tangent byZ211; no forced relation between rigid contact axis and its translational path.',
    peer_CAM_wire_check='NOT_TESTED',free_wire_shape='NOT_TESTED',continuous_sweep='NOT_TESTED',
    actual_crimped_envelope='BLOCKED',full_harness='BLOCKED',main_changed=False,approved=False,C6_main_applied=False,
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CONTACT_VERTICAL_DONE',r['status'],r['elapsed_s'],flush=True)
