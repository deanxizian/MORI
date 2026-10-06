"""Conditional staging above the head, including nominal PH bare contacts.

This covers free-end formation only. It does not assume that the subsequent
feed through the guide/neck has passed, nor adopt a new assembly sequence.
"""
from pathlib import Path
import itertools,json,sys,time,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'threading_formation'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
from curve_self_partition import self_clear
from cam_threading_geometry import parking,forming_u,service
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());B=REST/'bench_preassembly_v2';PH=REST/'PH_terminal_gate';C=REST/'return_clamp_v3';G=REST/'sliding_guide_v4';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',PH/'review.json',C/'review.json',G/'review.json',J/'join_review.json']
for path in reports:
    r=read(path);assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
br=read(reports[0]);inputs=reports+[B/'bench_curves.npz',J/'candidate_curves.npz',HERE/'cam_threading_geometry.py',HERE/'upper_curve_geometry.py']
def stored(path):
    inputs.append(path);a=np.load(path);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
original=ctx.targets;deferred=set(br['not_yet_installed'])|{'Plug_motion_J5'}
targets={n:t for n,t in original.items() if n not in deferred}
for n,p in [('Pitch_Cradle',C/'Pitch_Cradle_candidate.npz'),('Pitch_Yoke',G/'Pitch_Yoke_candidate.npz'),
            ('connector_band',C/'band.npz'),('connector_head',C/'head.npz'),('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz')]:targets[n]=ctx.target(stored(p))
ctx.targets=targets;allcurves=np.load(J/'candidate_curves.npz');bc=np.load(B/'bench_curves.npz')
fixed={};starts={};lengths={};parked={};terminals={};parkmeta={};arrays={}
def terminal(p,tangent):
    t=np.asarray(tangent);x=np.array([1.,0.,0.]);y=np.cross(t,x);y/=np.linalg.norm(y)
    tr=np.column_stack([x,y,t,np.asarray(p)])
    return manifold.Manifold.cube([2.08,1.5,5.7]).translate([-1.04,-.75,0.]).transform(tr)
def polylen(p):return float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
for pin in range(1,5):
    q=bc[f'CAM_{pin}']-[180,0,0];i=int(np.flatnonzero(q[:,2]>=224.6000061-1e-7)[0]);fixed[pin]=q[:i+1];starts[pin]=q[i]
    lengths[pin]=polylen(q)-polylen(fixed[pin]);free,m=parking(starts[pin],lengths[pin],-6*(pin-1));parked[pin]=np.vstack([fixed[pin][:-1],free]);parkmeta[pin]=m
    terminals[pin]=terminal(free[-1],m['terminal_tangent']);arrays[f'parking_pin{pin}']=parked[pin]
others={n:prepared(allcurves[n+'_y0'],.4445 if n.startswith('SPK_') else .5842,.0003) for n in ['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']}
def solid_hits(m,against):
    a=np.asarray(m.bounding_box());out=[]
    for n,t in against.items():
        if not(np.all(a[:3]<=t['hi']+.301) and np.all(a[3:]+.301>=t['lo'])):continue
        v=float((m^t['m']).volume());d=float(m.min_gap(t['m'],.301)) if abs(v)<1e-7 else 0.
        if abs(v)>1e-6 or d<.3-1e-5:out.append(dict(target=str(n),overlap_mm3=v,gap_mm=d))
    return out
def wire_vs_solid(p,m):
    t=ctx.target(m);ds=np.linalg.norm(np.diff(p,axis=0),axis=1);margin=.3302+.3+ds.max()/2+.0004
    ids=np.flatnonzero(np.all(p>=t['lo']-margin,axis=1)&np.all(p<=t['hi']+margin,axis=1))
    for i in ids:
        d=float(t['tree'].find_nearest(Vector(p[i]))[3])
        if d<margin:return dict(point_mm=p[i].tolist(),distance_mm=d,required_mm=margin)
    return None
parkchecks=[]
for pin in range(1,5):
    p=parked[pin];free=p[len(fixed[pin])-1:]
    native=ctx.clear(free[1:],radius=.3302,chord_error=.0003)
    th=solid_hits(terminals[pin],targets);wh=[];tt=[]
    for peer in range(1,5):
        if peer==pin:continue
        hit=wire_vs_solid(parked[peer],terminals[pin])
        if hit:wh.append(dict(peer=peer,**hit))
        tt+=solid_hits(terminals[pin],{peer:ctx.target(terminals[peer])})
    parkchecks.append(dict(pin=pin,status='PASS' if not native and not th and not wh and not tt else 'BLOCKED',native=native,terminal_native=th,terminal_wires=wh,terminal_terminals=tt))
print('THREAD_PARK',parkchecks,flush=True)
rows=[];summaries=[];first={}
for pin in range(1,5):
    # Earlier pins are only a conditional final-route fixture. Their actual
    # intervening threading/forming has NOT been proved by this study.
    peerpaths={p:(allcurves[f'CAM_{p}_y0_p0'][::-1] if p<pin else parked[p]) for p in range(1,5) if p!=pin}
    pp={p:prepared(q,.3302,.0003) for p,q in peerpaths.items()}
    peerterms={p:ctx.target(terminals[p]) for p in range(pin+1,5)}
    cases=[]
    for u in np.linspace(0,1,max(2,12*(pin-1)+1)):
        cases.append(('unpark',float(u),parking(starts[pin],lengths[pin],-6*(pin-1)*(1-u))))
    for a in np.linspace(0,math.pi,73):cases.append(('turn',float(a),forming_u(starts[pin],lengths[pin],float(a))))
    for u in np.linspace(0,1,21):
        anchor=(1-u)*np.array([starts[pin][0],starts[pin][1]+14,270.])+u*np.array([-26.8,-11.,270.])
        cases.append(('approach',float(u),service(starts[pin],lengths[pin],anchor)))
    completed=0
    for stage,t,(free,m) in cases:
        p=np.vstack([fixed[pin][:-1],free]);fullL=polylen(p);reference=polylen(bc[f'CAM_{pin}']);err=abs(fullL-reference)
        assert err<.01,(pin,stage,t,err)
        native=ctx.clear(free[1:],radius=.3302,chord_error=m['curve_error_mm']);bare=terminal(free[-1],m['terminal_tangent'])
        solid=solid_hits(bare,targets);term=solid_hits(bare,peerterms);wire=[]
        for peer,q in peerpaths.items():
            hit=wire_vs_solid(q,bare)
            if hit:wire.append(dict(peer=peer,**hit))
        item=prepared(p,.3302,max(.0003,m['curve_error_mm']));pairs=[]
        for peer,other in {**pp,**others}.items():
            r=pair_threshold(item,other)
            if r['status']!='PASS':pairs.append(dict(peer=str(peer),**r))
        # The other terminals must also clear the moving wire.
        for peer,target in peerterms.items():
            hit=wire_vs_solid(p,target['m'])
            if hit:wire.append(dict(parked_terminal=peer,**hit))
        ok=not native and not solid and not term and not wire and not pairs
        row=dict(pin=pin,stage=stage,parameter=t,status='PASS' if ok else 'BLOCKED',length_error_mm=err,
                 terminal_rear_mm=free[-1].tolist(),terminal_tangent=m['terminal_tangent'],native=native,terminal_native=solid,
                 terminal_terminals=term,terminal_wires=wire,wire_pairs=pairs)
        rows.append(row);completed+=1
        if not ok:
            first[str(pin)]=row;arrays[f'blocked_pin{pin}']=p;break
        if (stage=='turn' and abs(t-math.pi)<1e-8) or (stage=='approach' and t==1):arrays[f'{stage}_pin{pin}']=p
    summaries.append(dict(pin=pin,checked=completed,planned=len(cases),status='PASS' if str(pin) not in first else 'BLOCKED'))
    print('THREAD_FORMATION_PIN',pin,summaries[-1],first.get(str(pin)),flush=True)
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'states.npz',**arrays)
r=dict(status='PASS' if all(x['status']=='PASS' for x in parkchecks+summaries) else 'BLOCKED',
    scope='Conditional above-head formation before guide feed; earlier pins in final-route fixtures do not prove their intervening feed',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},parked_checks=parkchecks,
    summaries=summaries,rows=rows,first_failures=first,terminal_nominal_box_mm=[2.08,1.5,5.7],terminal_evidence='PH generic catalogue outline; actual selected crimped shape remains BLOCKED',
    staging_rear_plane_z_mm=270.,minimum_curve_radius_mm=7.,length_tolerance_mm=.01,
    main_changed=False,approved=False,C6_main_applied=False,whole_feed='NOT_TESTED',continuous_forming='NOT_TESTED',physical_assembly='NOT_TESTED',full_harness='BLOCKED',
    states_sha256=sha(OUT/'states.npz'),script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('THREAD_FORMATION_DONE',r['status'],r['elapsed_s'],flush=True)
