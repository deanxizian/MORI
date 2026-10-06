"""Check a bounded temporary parking family before attempting full wire feed.

This cannot validate neck threading or later restoration by itself. All
assumed contacts, unapproved guide/C6 dependencies and omitted parts are kept
explicit. No main scene or hardware-owned files are edited.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
OUT=REST/'temporary_parking';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import refined
from cam_threading_geometry import parking,service
from cam_temporary_staging_geometry import service_with_lead
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',REST/'PH_terminal_gate/review.json',REST/'threading_descent/review.json']
inputs=reports+[B/'bench_curves.npz',J/'candidate_curves.npz',HERE/'cam_threading_geometry.py',HERE/'cam_temporary_staging_geometry.py',BASE/'CAM_PH_RECEIPT.json']
for path in reports:
    r=read(path);assert r['status'] in ['PASS','BLOCKED']
    for file,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/file)==h,file
original=ctx.targets;deferred=set(read(reports[0])['not_yet_installed'])|{'Plug_motion_J5'}
targets={n:t for n,t in original.items() if n not in deferred}
def stored(path):
    inputs.append(path);a=np.load(path);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    assert m.status()==manifold.Error.NoError;return m
for name,path in [('Pitch_Cradle',C/'Pitch_Cradle_candidate.npz'),('Pitch_Yoke',G/'Pitch_Yoke_candidate.npz'),
                  ('connector_band',C/'band.npz'),('connector_head',C/'head.npz'),('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz')]:
    targets[name]=ctx.target(stored(path))
ctx.targets=targets;bc=np.load(B/'bench_curves.npz');allcurves=np.load(J/'candidate_curves.npz')
fixed={};starts={};lengths={};parked={};terminals={};arrays={}
polylen=lambda p:float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
def terminal(p,tangent):
    t=np.asarray(tangent);x=np.array([1.,0.,0.]);y=np.cross(t,x);y/=np.linalg.norm(y)
    return manifold.Manifold.cube([2.08,1.5,5.7]).translate([-1.04,-.75,0.]).transform(np.column_stack([x,y,t,p]))
for pin in range(1,5):
    q=bc[f'CAM_{pin}']-[180,0,0];i=int(np.flatnonzero(q[:,2]>=224.6000061-1e-7)[0]);fixed[pin]=q[:i+1];starts[pin]=q[i]
    lengths[pin]=polylen(q)-polylen(fixed[pin]);free,meta=parking(starts[pin],lengths[pin],-6*(pin-1))
    parked[pin]=np.vstack([fixed[pin][:-1],free]);terminals[pin]=terminal(free[-1],meta['terminal_tangent'])
others={n:prepared(refined(allcurves[n+'_y0'],.01),.4445 if n.startswith('SPK_') else .5842,.0003) for n in ['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']}
def solid_hits(m,against):
    box=np.asarray(m.bounding_box());hits=[]
    for name,target in against.items():
        if not(np.all(box[:3]<=target['hi']+.301) and np.all(box[3:]+.301>=target['lo'])):continue
        overlap=float((m^target['m']).volume());gap=float(m.min_gap(target['m'],.301)) if abs(overlap)<1e-7 else 0.
        if abs(overlap)>1e-6 or gap<.3-1e-5:hits.append(dict(target=str(name),overlap_mm3=overlap,gap_mm=gap))
    return hits
def wire_vs_solid(p,m):
    target=ctx.target(m);margin=.3302+.3+np.linalg.norm(np.diff(p,axis=0),axis=1).max()/2+.0004
    ids=np.flatnonzero(np.all(p>=target['lo']-margin,axis=1)&np.all(p<=target['hi']+margin,axis=1))
    for i in ids:
        d=float(target['tree'].find_nearest(Vector(p[i]))[3])
        if d<margin:return dict(point_mm=p[i].tolist(),distance_mm=d,required_mm=margin)
    return None
def check(pin,free,meta,peers,peerterm):
    p=np.vstack([fixed[pin][:-1],free]);error=abs(polylen(p)-polylen(bc[f'CAM_{pin}']));assert error<.01
    bare=terminal(free[-1],meta['terminal_tangent']);native=ctx.clear(free[1:],radius=.3302,chord_error=meta['curve_error_mm'])
    solid=solid_hits(bare,targets);term=solid_hits(bare,{k:ctx.target(v) for k,v in peerterm.items()});wire=[];pairs=[]
    for peer,q in peers.items():
        hit=wire_vs_solid(q,bare)
        if hit:wire.append(dict(peer=peer,**hit))
    item=prepared(p,.3302,max(.0003,meta['curve_error_mm']))
    for peer,other in {**{k:prepared(refined(q,.01),.3302,.0003) for k,q in peers.items()},**others}.items():
        result=pair_threshold(item,other)
        if result['status']!='PASS':pairs.append(dict(peer=str(peer),**result))
    for peer,m in peerterm.items():
        hit=wire_vs_solid(p,m)
        if hit:wire.append(dict(parked_terminal=peer,**hit))
    return p,bare,dict(status='BLOCKED' if native or solid or term or wire or pairs else 'PASS',length_error_mm=error,
        terminal_rear_mm=free[-1].tolist(),native=native,terminal_native=solid,terminal_terminals=term,terminal_wires=wire,wire_pairs=pairs)

# Only test the proposed completed parking states first. If even these do not
# fit, there is no reason to imply that the connecting motion can be adopted.
layout={1:np.array([-30.15,-11.5,218.]),2:np.array([-30.15,-10.5,211.]),3:np.array([-29.2,-11.,204.])}
rows=[];states={};state_terms={};finals={}
for pin in [1,2,3]:
    free,meta=service_with_lead(starts[pin],lengths[pin],layout[pin],lead=230.-layout[pin][2])
    states[pin]=np.vstack([fixed[pin][:-1],free]);state_terms[pin]=terminal(free[-1],meta['terminal_tangent']);finals[pin]=(free,meta)
static=[]
for pin in [1,2,3]:
    peers={p:(states[p] if p< pin else parked[p]) for p in range(1,5) if p!=pin}
    peerterms={p:(state_terms[p] if p< pin else terminals[p]) for p in range(1,5) if p!=pin}
    p,m,row=check(pin,*finals[pin],peers,peerterms);row.update(pin=pin,stage='temporary_parked_state')
    static.append(row);arrays[f'parked_candidate_pin{pin}']=p
    print('TEMP_PARK_STATE',pin,row,flush=True)

# Advance only if every temporary state clears. These finite connecting
# samples still do not include neck feed, hand access, or restoration.
transitions=[]
if all(x['status']=='PASS' for x in static):
    for pin in [1,2,3,4]:
        peers={p:(states[p] if p<pin else parked[p]) for p in range(1,5) if p!=pin}
        peerterms={p:(state_terms[p] if p<pin else terminals[p]) for p in range(1,5) if p!=pin}
        planned=[]
        for lead in np.linspace(3,16,27):planned.append(('extend_stem',float(lead),service_with_lead(starts[pin],lengths[pin],[-26.8,-11.,270.],lead=float(lead))))
        for z in np.linspace(270.,218.,209):planned.append(('descend',float(z),service_with_lead(starts[pin],lengths[pin],[-26.8,-11.,float(z)],lead=16.)))
        if pin<4:
            for u in np.linspace(0,1,53):
                anchor=(1-u)*np.array([-26.8,-11.,218.])+u*layout[pin]
                planned.append(('move_to_park',float(u),service_with_lead(starts[pin],lengths[pin],anchor,lead=(1-u)*16+u*(230-layout[pin][2]))))
        failed=None
        for stage,t,(free,meta) in planned:
            p,m,row=check(pin,free,meta,peers,peerterms);row.update(pin=pin,stage=stage,parameter=t);transitions.append(row)
            if row['status']!='PASS':failed=row;arrays[f'blocked_transition_pin{pin}']=p;break
        print('TEMP_PARK_TRANSITION',pin,'BLOCKED' if failed else 'PASS',failed,flush=True)
        if failed:break
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'states.npz',**arrays)
status='PASS' if all(x['status']=='PASS' for x in static) and transitions and all(x['status']=='PASS' for x in transitions) else 'BLOCKED'
report=dict(status=status,scope='Bounded temporary parking state family and conditional connecting samples only',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},
    temporary_positions_mm={str(k):v.tolist() for k,v in layout.items()},static_states=static,transition_samples=transitions,
    nominal_PH_contact_mm=[2.08,1.5,5.7],contact_selection='BLOCKED',wire_diameter_mm=.6604,
    wire_evidence='Existing Alpha2841/7 planning sample; formal SPH002 minimum insulation OD remains incompatible. No source substitution.',
    minimum_bend_radius_assumed_mm=7.,not_yet_installed=sorted(deferred),Yaw_Reaction_Link_present=True,
    initial_unpark_and_turn_with_new_peers='NOT_TESTED',neck_feed='NOT_TESTED',restore_final_shape='NOT_TESTED',hand_access='NOT_TESTED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',physical_assembly='NOT_TESTED',
    states_sha256=sha(OUT/'states.npz'),script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('TEMP_PARK_DONE',status,report['elapsed_s'],flush=True)
