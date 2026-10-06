"""Check the full first-wire arrival state after a rigid neck path was found.

This cannot validate neck threading or later restoration by itself. All
assumed contacts, unapproved guide/C6 dependencies and omitted parts are kept
explicit. No main scene or hardware-owned files are edited.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
OUT=REST/'wire_body_arrival';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import refined
from cam_threading_geometry import parking,service
from cam_temporary_staging_geometry import service_with_lead
from curve_self_partition import self_clear
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',REST/'PH_terminal_gate/review.json',REST/'threading_descent/review.json']
inputs=reports+[B/'bench_curves.npz',J/'candidate_curves.npz',HERE/'cam_threading_geometry.py',HERE/'cam_temporary_staging_geometry.py',BASE/'CAM_PH_RECEIPT.json',REST/'contact_continuous/review.json',REST/'contact_continuous/path.npz']
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

# Test a complete first-wire arrival state before inferring a feed motion.
source=allcurves['CAM_1_y0_p0'];guide=np.array([-26.600000143051147,-11.,224.])
i=int(np.argmin(np.linalg.norm(source-guide,axis=1)));assert np.linalg.norm(source[i]-guide)<1e-6
neck=source[:i+1][::-1];cut_z=158.
i=int(np.flatnonzero(neck[:,2]<=cut_z)[0]);neck=neck[:i+1].copy()
u=(cut_z-neck[-2,2])/(neck[-1,2]-neck[-2,2]);neck[-1]=neck[-2]+u*(neck[-1]-neck[-2])
contact=np.load(REST/'contact_continuous/path.npz');end=contact['rear_mm'][-1]
a=neck[-1];direction=(neck[-1]-neck[-2])/(neck[-1,2]-neck[-2,2]);dz=end[2]-a[2]
d0=direction*dz;d1=np.array([0.,0.,dz]);control=np.array([a,a+d0/3,end-d1/3,end])
# Constant-Z derivative gives a conservative positive speed bound; cubic
# acceleration is linear, so its maximum norm is attained at an endpoint.
accmax=max(np.linalg.norm(6*(control[2]-2*control[1]+control[0])),np.linalg.norm(6*(control[3]-2*control[2]+control[1])))
bend_bound=dz*dz/accmax;n=3001;t=np.linspace(0,1,n)
bezier=(1-t)[:,None]**3*control[0]+3*((1-t)**2*t)[:,None]*control[1]+3*((1-t)*t*t)[:,None]*control[2]+t[:,None]**3*control[3]
chord_error=accmax/(8*(n-1)**2)
neck=np.vstack([neck[:-1],bezier]);neck=refined(neck,.01);neckL=polylen(neck)
upper,meta=service(starts[1],lengths[1]-neckL,guide)
meta['curve_error_mm']=max(.0003,chord_error,meta['curve_error_mm']);free=np.vstack([upper[:-1],neck])
p,m,row=check(1,free,meta,{k:v for k,v in parked.items() if k!=1},{k:v for k,v in terminals.items() if k!=1})
self_review=self_clear(prepared(p,.3302,meta['curve_error_mm']));row['self_review']=self_review
if self_review['status']!='PASS' or bend_bound<7:row['status']='BLOCKED'
arrays['arrival_wire']=p;arrays['neck_curve']=neck;arrays['upper_curve']=upper;arrays['cubic_controls']=control
for k in range(2,5):arrays[f'parked_pin{k}']=parked[k]
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'state.npz',**arrays)
report=dict(status=row['status'],scope='Complete first CAM wire body-arrival static candidate; feed motion and later wires not proved',
 sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},row=row,
 cubic_join_z_mm=cut_z,cubic_bend_radius_lower_bound_mm=float(bend_bound),cubic_chord_error_mm=float(chord_error),
 cubic_controls_mm=control.tolist(),cubic_tangent_basis='Finite reference-polyline tangent at trim point; exact analytic join remains unqualified',
 neck_length_mm=neckL,total_free_length_mm=lengths[1],nominal_wire_diameter_mm=.6604,
 parked_peer_pins=[2,3,4],other_upper_candidate_wires=list(others),Yaw_Reaction_Link_present=True,
 not_yet_installed=sorted(deferred),actual_crimped_envelope='BLOCKED',feed_motion='NOT_TESTED',full_sequence='BLOCKED',
 main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',physical_assembly='NOT_TESTED',
 state_sha256=sha(OUT/'state.npz'),script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('WIRE_BODY_ARRIVAL_DONE',report['status'],row,'cubic_R_bound',bend_bound,report['elapsed_s'],flush=True)
