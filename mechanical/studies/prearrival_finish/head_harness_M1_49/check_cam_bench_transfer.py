"""Finite transfer of the populated CAM/cradle and its upward loose leads.

The robot stays present. Optics, head shells and short shafts are explicitly
scheduled later. This does not stand in for final threading or wire forming.
"""
from pathlib import Path
import json,sys,time,itertools
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';OUT=REST/'bench_transfer'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
from mathutils.kdtree import KDTree
from bounded_curve_checks import pair_threshold
from curve_self_partition import self_clear
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());br=read(B/'review.json')
assert br['status']=='PASS'
for f,h in {**br['sources'],**br['inputs']}.items():assert sha(ROOT/f)==h,f
for f,h in br['output_geometry'].items():assert sha(B/f)==h,f
inputs=[B/'review.json',B/'bench_curves.npz',G/'review.json',G/'Pitch_Yoke_candidate.npz']
def stored(p):
    inputs.append(p);a=np.load(p);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
module=set(br['module'])|{'connector_band','connector_head'};deferred=set(br['not_yet_installed'])
moving={n:ctx.ss[n].m for n in br['module']}
for n in ['Pitch_Cradle','connector_band','connector_head']:moving[n]=stored(B/(n+'.npz')).translate([-180,0,0])
fixed={n:t for n,t in ctx.targets.items() if n not in module|deferred}
fixed['Pitch_Yoke']=ctx.target(stored(G/'Pitch_Yoke_candidate.npz'))
curves={n:p-[180,0,0] for n,p in np.load(B/'bench_curves.npz').items()}
def pack(p,r):
    tree=KDTree(len(p))
    for i,v in enumerate(p):tree.insert(Vector(v),i)
    tree.balance()
    return dict(p=p,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),error=.0003,
                radius=r,tree=tree,lo=p.min(0),hi=p.max(0))
packs={n:pack(p,.3302) for n,p in curves.items()}
selfrows={n:self_clear(a) for n,a in packs.items()}
pairrows={a+'_'+b:pair_threshold(packs[a],packs[b]) for a,b in itertools.combinations(packs,2)}
fullp=BASE/'cam_side_fans/c6_join/candidate_curves.npz';inputs.append(fullp);full=np.load(fullp)
othernames=['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']
other={n:pack(full[f'{n}_y0'],.4445 if n.startswith('SPK_') else .5842) for n in othernames}
waypoints=np.array([[180,0,0],[180,0,80],[0,0,80],[0,0,0]],float)
movingbounds={n:np.asarray(m.bounding_box()) for n,m in moving.items()}
names=list(fixed);los=np.array([fixed[n]['lo'] for n in names]);his=np.array([fixed[n]['hi'] for n in names])
original=ctx.targets;ctx.targets=fixed;rows=[];hits=[];wirehits=[];crosshits=[];pairs=0;poses=0
for segment,(start,end) in enumerate(zip(waypoints,waypoints[1:])):
    step=.25;count=int(np.ceil(np.linalg.norm(end-start)/step));near=[];min_gap=.126
    for j,shift in enumerate(np.linspace(start,end,count+1)):
        poses+=1
        for n,m in moving.items():
            box=movingbounds[n];lo=box[:3]+shift;hi=box[3:]+shift
            ids=np.flatnonzero(np.all(lo<=his+.126,axis=1)&np.all(hi+.126>=los,axis=1))
            if not len(ids):continue
            tr=m.translate(shift.tolist())
            for i in ids:
                name=names[i];t=fixed[name]['m'];pairs+=1
                v=float((tr^t).volume());d=float(tr.min_gap(t,.126)) if abs(v)<1e-7 else 0.
                min_gap=min(min_gap,d)
                if abs(v)>1e-6:hits.append(dict(segment=segment,sample=j,shift_mm=shift.tolist(),moving=n,fixed=name,overlap_mm3=v))
                elif d<=.125+1e-5 and len(near)<12:near.append(dict(sample=j,shift_mm=shift.tolist(),moving=n,fixed=name,gap_mm=d))
            if len(hits)>12:break
        for n,p in curves.items():
            q=p+shift;hit=ctx.clear(q,radius=.3302,chord_error=.0003)
            if hit:wirehits.append(dict(segment=segment,sample=j,wire=n,shift_mm=shift.tolist(),**hit))
            # Move a copied packed center line; the stationary tree belongs to
            # each already placed other wire, so build only when broad boxes meet.
            lo=q.min(0);hi=q.max(0)
            for othername,b in other.items():
                margin=.3302+b['radius']+.3+packs[n]['step']+b['step']+.001
                if not (np.all(lo<=b['hi']+margin) and np.all(hi+margin>=b['lo'])):continue
                a=pack(q,.3302);r=pair_threshold(a,b)
                if r['status']!='PASS':crosshits.append(dict(segment=segment,sample=j,wire=n,other=othername,shift_mm=shift.tolist(),**r))
        if len(hits)>12 or len(wirehits)>12 or len(crosshits)>12:break
    rows.append(dict(segment=segment,start_mm=start.tolist(),end_mm=end.tolist(),sample_step_mm=step,
                     samples_completed=j+1,planned_samples=count+1,min_sampled_rigid_gap_bound_mm=min_gap,
                     rigid_continuous_clearance_bound_mm=max(0.,min_gap-step/2),close_rigid_samples=near))
    print('BENCH_TRANSFER_SEGMENT',segment,j+1,'rigid',hits[:2],'wire',wirehits[:2],'cross',crosshits[:2],flush=True)
    if hits or wirehits or crosshits:break
ctx.targets=original;ctx.assert_unchanged()
status='PASS' if not hits and not wirehits and not crosshits and all(r['status']=='PASS' for r in [*selfrows.values(),*pairrows.values()]) and len(rows)==3 else 'BLOCKED'
r=dict(status=status,scope='Finite .25mm translation samples of the detached populated cradle and loose upward body-end leads; later thread/form/mate stage not checked',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},main_changed=False,approved=False,
    moving=sorted(module),not_yet_installed=sorted(deferred),fixed_objects=sorted(fixed),waypoints_mm=waypoints.tolist(),
    samples=poses,rigid_close_pairs=pairs,stages=rows,rigid_hits=hits,wire_hits=wirehits,other_wire_hits=crosshits,
    loose_wire_remote_self=selfrows,loose_wire_mutual=pairrows,
    body_end_housing='PHR-4 absent; bare contacts and hand/fixture envelopes not yet qualified',
    no_native_obstacles_silently_removed=True,body_and_other_seven_candidate_routes_present=True,
    later_threading_forming_and_mating='NOT_TESTED',physical_assembly='NOT_TESTED',full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('BENCH_TRANSFER_DONE',status,r['elapsed_s'],flush=True)
