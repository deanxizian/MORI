"""Explicit detached CAM/cradle assembly with equal-length free body-end leads.

This does not prove later threading or wiring deformation. It tests a real
separate bench placement, retaining the installed robot as an obstacle.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'bench_preassembly_v2'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold,P
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
C=REST/'return_clamp_v3';G=REST/'sliding_guide_v4';J=BASE/'cam_side_fans/c6_join'
reports=[read(p/'review.json') for p in [C,G]]+[read(J/'join_review.json')]
for r in reports:
    assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(J/'candidate_curves.npz')==reports[-1]['curve_sha256']
full=np.load(J/'candidate_curves.npz');inputs=[C/'review.json',G/'review.json',J/'join_review.json',J/'candidate_curves.npz']
def stored(p):
    inputs.append(p);a=np.load(p)
    m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    assert m.status()==manifold.Error.NoError;return m
def save(name,m):
    a=m.to_mesh64();np.savez_compressed(OUT/(name+'.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
shift=np.array([180.,0.,0.])
module={'Pitch_Cradle','CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}
module|={r['id'] for r in P['interface_completion']['inserts'] if r['host']=='Pitch_Cradle'}
module|={n for n in ctx.ss if n.startswith('CAM_Mount_Screw_')}
assert module<=set(ctx.ss)
# These optical, shell and transmission parts have not yet been installed.
# The two servos, pitch bearings and entire yaw yoke remain in the robot.
old=HERE.parent/'cam_retention_M1_48/tools_and_tail.json';oldr=read(old);inputs.append(old)
deferred=set(oldr['not_yet_installed']);assert not module&deferred
targets={n:t['m'] for n,t in ctx.targets.items() if n not in deferred}
targets['Pitch_Yoke']=stored(G/'Pitch_Yoke_candidate.npz')
targets['Pitch_Cradle']=stored(C/'Pitch_Cradle_candidate.npz')
for n in module:targets[n]=targets[n].translate(shift.tolist())
for n in ['band','head']:targets['connector_'+n]=stored(C/(n+'.npz')).translate(shift.tolist())
curves={};stations=[]
for pin in range(1,5):
    q=full[f'CAM_{pin}_y0_p0'];x=-26.600000143051147-pin+1
    line=(np.abs(q[:,0]-x)<1e-5)&(np.abs(q[:,1]+20.800000190734863)<1e-5)
    ids=np.flatnonzero(line[:-1]&line[1:]&(q[:-1,2]>=224.6000061)&(q[1:,2]<224.6000061));assert len(ids)==1
    i=int(ids[0]);f=(224.6000061-q[i,2])/(q[i+1,2]-q[i,2]);clamp=q[i]+f*(q[i+1]-q[i])
    fixed=np.vstack([clamp,q[i+1:]])[::-1]
    length=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
    fixedlen=float(np.linalg.norm(np.diff(fixed,axis=0),axis=1).sum());free=length-fixedlen
    freecurve=clamp+np.linspace(0,free,int(np.ceil(free/.03))+1)[:,None]*[0,0,1]
    p=np.vstack([fixed,freecurve[1:]])+shift
    curves[f'CAM_{pin}']=p
    err=abs(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())-length);assert err<1e-6
    stations.append(dict(pin=pin,length_mm=length,unchanged_from_CAM_mm=fixedlen,
        loose_body_lead_mm=free,length_error_mm=err,loose_end_world_mm=p[-1].tolist()))
np.savez_compressed(OUT/'bench_curves.npz',**curves)
def close_boxes(a,b,gap=.301):
    a=np.asarray(a.bounding_box());b=np.asarray(b.bounding_box())
    return bool(np.all(a[:3]<=b[3:]+gap) and np.all(a[3:]+gap>=b[:3]))
def toolcheck(m):
    hits=[];intended=[]
    for n,t in targets.items():
        if not close_boxes(m,t):continue
        v=float((m^t).volume());d=float(m.min_gap(t,.301)) if abs(v)<1e-7 else 0.
        row=dict(target=n,overlap_mm3=v,gap_mm=d)
        if n in ['connector_band','connector_head']:
            intended.append(row)
            if abs(v)>1e-5:hits.append(row)
        elif abs(v)>1e-6 or d<.3-1e-5:hits.append(row)
    tg=ctx.target(m);wires=[]
    for n,p in curves.items():
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
        bound=.3302+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0004
        ids=np.flatnonzero(np.all(p>=tg['lo']-bound[:,None],axis=1)&np.all(p<=tg['hi']+bound[:,None],axis=1))
        for i in ids:
            d=float(tg['tree'].find_nearest(Vector(p[i]))[3])
            if d<bound[i]:wires.append(dict(wire=n,point_mm=p[i].tolist(),distance_mm=d,required_mm=float(bound[i])));break
    return dict(status='PASS' if not hits and not wires else 'BLOCKED',native_hits=hits,wire_hits=wires,intended_tie_operation=intended)
OLD=HERE.parent/'cam_retention_M1_48';results=[]
for name in ['connector_0_cutter_sweep']+[f'connector_tail_{i}' for i in range(6)]:
    m=stored(OLD/(name+'.npz')).translate((shift+[-17.97,0,3.]).tolist())
    rr=toolcheck(m);rr['name']=name;results.append(rr);save(name,m)
    print('BENCH_TOOL',name,rr,flush=True)
# The fixed board-port return is unchanged. Check only the newly straightened
# free lead, excluding the narrow intentional grip band of its own tie/bed.
wire_hits=[];original=ctx.targets
ctx.targets={n:ctx.target(m) for n,m in targets.items()}
for pin in range(1,5):
    p=curves[f'CAM_{pin}'];new=p[p[:,2]>224.6001061]
    # Above the previously checked complete 15 mm grip/return straight only;
    # every point below that plane was copied unchanged from the input path.
    x=-26.600000143051147-pin+1+shift[0]
    new=new[(np.abs(new[:,0]-x)<1e-5)&(np.abs(new[:,1]+20.800000190734863)<1e-5)]
    assert len(new)>1000
    hit=ctx.clear(new,radius=.3302,chord_error=.0003)
    if hit:wire_hits.append(dict(pin=pin,**hit))
ctx.targets=original
# Detached module versus the remaining robot, including its yoke and servos.
module_names=module|{'connector_band','connector_head'};module_hits=[];checks=0
for n in module_names:
    for name,t in targets.items():
        if name in module_names:continue
        checks+=1
        if not close_boxes(targets[n],t):continue
        v=float((targets[n]^t).volume());d=float(targets[n].min_gap(t,.301)) if abs(v)<1e-7 else 0.
        if abs(v)>1e-6 or d<.3-1e-5:module_hits.append(dict(moving=n,fixed=name,overlap_mm3=v,gap_mm=d))
ctx.assert_unchanged()
for n in ['Pitch_Cradle','connector_band','connector_head']:save(n,targets[n])
r=dict(status='PASS' if results[0]['status']=='PASS' and any(x['status']=='PASS' for x in results[1:]) and not wire_hits and not module_hits else 'BLOCKED',
    scope='Detached CAM+cradle bench placement and equal-length upward free body-end leads; cutter and loose-tail workspace only',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},
    main_changed=False,approved=False,module=sorted(module),not_yet_installed=sorted(deferred),bench_translation_mm=shift.tolist(),
    remaining_robot_included=True,servos_retained_in_robot=True,module_separation_checks=checks,module_hits=module_hits,
    free_lead_native_hits=wire_hits,unchanged_return_top_z_mm=224.6000061,stations=stations,tool_results=results,
    body_end_housing='PHR-4 deliberately NOT installed; real SPH contact and crimp feed envelope not checked',
    CAM_end_status='Existing photo-based port and wire return unchanged; no new electrical or crimp qualification',
    later_wire_threading='NOT_TESTED',later_cradle_insertion='NOT_TESTED',physical_cutting_and_grip='NOT_TESTED',
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('BENCH_PREASSEMBLY_DONE',r['status'],wire_hits,module_hits,r['elapsed_s'],flush=True)
