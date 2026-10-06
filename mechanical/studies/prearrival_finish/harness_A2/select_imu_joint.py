# -*- coding: utf-8 -*-
"""Select a simultaneously separated eight-wire IMU candidate from pools."""
from pathlib import Path
import json,hashlib,time,itertools,sys,collections
import numpy as np
HERE=Path(__file__).resolve().parent
WIDE='--wide' in sys.argv
ASSEMBLY='--assembly' in sys.argv
SIDE_PATH='--side-path' in sys.argv
SLOT_PATH='--deck-slot' in sys.argv
REFINED='--refined' in sys.argv
DIAGNOSE='--diagnose' in sys.argv
ARC_PRUNE='--arc-prune' in sys.argv
MAX_SECONDS=float(sys.argv[sys.argv.index('--max-seconds')+1]) if '--max-seconds' in sys.argv else 150.
SOURCE=HERE/('imu_refined_assembly_pools.json' if REFINED else 'imu_slot_assembly_pools.json' if SLOT_PATH and ASSEMBLY else 'imu_slot_pools.json' if SLOT_PATH else 'imu_side_assembly_pools.json' if ASSEMBLY and SIDE_PATH else 'imu_side_pools.json' if SIDE_PATH else 'imu_assembly_pools.json' if ASSEMBLY else 'imu_wide_pools.json' if WIDE else 'imu_individual_pools.json')
OUT_STEM='imu_refined_assembly_joint' if REFINED else 'imu_slot_assembly_joint' if SLOT_PATH and ASSEMBLY else 'imu_slot_joint' if SLOT_PATH else 'imu_side_assembly_joint' if ASSEMBLY and SIDE_PATH else 'imu_side_joint' if SIDE_PATH else 'imu_assembly_joint' if ASSEMBLY else 'imu_wide_joint' if WIDE else 'imu_joint_selected'
if '--pool' in sys.argv:
    SOURCE=HERE/sys.argv[sys.argv.index('--pool')+1]
    assert SOURCE.parent==HERE
if '--output-prefix' in sys.argv:
    OUT_STEM=sys.argv[sys.argv.index('--output-prefix')+1]
    assert Path(OUT_STEM).name==OUT_STEM
if DIAGNOSE:OUT_STEM+='_diagnostic'
data=json.loads(SOURCE.read_text());pools=data['pools']
assert data['status']=='PASS'
code=(HERE/'select_joint.py').read_text()
exec(code[code.index('def samples'):code.index('sampled=')])
exec(code[code.index('def exact_segment_min'):code.index('selected=search')])
routes={(p,i):r for p,rows in pools.items() for i,r in enumerate(rows)}
coarse={k:samples(r['curve_mm'],.7) for k,r in routes.items()}
cache={};calls=0;nodes=0;start=time.time();last=start;diagnostics={}
required=1.016+.3401 # .04 for sweep inflation and .0001 for final numerical allowance
def compatible(a,b):
    global calls
    k=tuple(sorted([a,b]));calls+=1
    if k in cache:return cache[k]
    A=coarse[a];B=coarse[b];v=np.diff(B,axis=0);w=A[:,None,:]-B[:-1][None,:,:]
    tt=np.clip(np.sum(w*v[None,:,:],axis=2)/np.maximum(np.sum(v*v,axis=1),1e-12),0,1)
    distances=np.linalg.norm(w-tt[:,:,None]*v[None,:,:],axis=2)
    d=float(np.min(distances))
    if d>=required+.40:ok=True
    elif d<required-.04:ok=False
    else:ok=exact_segment_min(routes[a]['curve_mm'],routes[b]['curve_mm'])[0]>=required
    cache[k]=ok
    if DIAGNOSE:
        pair=tuple(sorted((a[0],b[0])))
        q=diagnostics.setdefault(pair,dict(checked=0,compatible=0,best_coarse_center_gap_mm=-1.))
        q['checked']+=1;q['compatible']+=int(ok)
        if d>q['best_coarse_center_gap_mm']:
            i,j=np.unravel_index(np.argmin(distances),distances.shape)
            near=B[j]+tt[i,j]*v[j]
            q.update(best_coarse_center_gap_mm=d,candidates=[list(a),list(b)],
                nearest_points_mm=[A[i].tolist(),near.tolist()],
                route_sides=[routes[a]['route_side'],routes[b]['route_side']])
    return ok
best=[];limited=False
def search(allowed,chosen):
    global nodes,best,last,limited
    nodes+=1
    if len(chosen)>len(best):best=chosen[:]
    if time.time()-last>10:
        print('IMU_JOINT_PROGRESS',nodes,len(cache),'best',len(best),flush=True);last=time.time()
        (HERE/(OUT_STEM+'_progress.json')).write_text(json.dumps(dict(nodes=nodes,pairs=len(cache),best_count=len(best),elapsed_s=time.time()-start))+'\n')
    if not allowed:return chosen
    if nodes>200000 or time.time()-start>MAX_SECONDS:limited=True;return None
    p=min(allowed,key=lambda q:len(allowed[q]));order=allowed[p]
    for idx in order:
        key=(p,idx);next_allowed={};bad=False
        for q,ids in allowed.items():
            if q==p:continue
            good=[j for j in ids if compatible(key,(q,j))]
            if not good:bad=True;break
            next_allowed[q]=good
        if bad:continue
        ans=search(next_allowed,chosen+[key])
        if ans:return ans
        if limited:return None
    return None
allowed={p:sorted(range(len(rows)),key=lambda i:rows[i]['geometric_centerline_length_mm']) for p,rows in pools.items()}
arc_summary=None
if ARC_PRUNE:
    # Adjacent native pins are usually the tightest wire pairs. Remove a
    # candidate only if it has no compatible neighbor candidate. This cannot
    # remove a complete valid assignment; all non-adjacent pairs remain in
    # the exact final audit and forward-checking search.
    before_counts={p:len(v) for p,v in allowed.items()}
    neighbours={p:[q for q in allowed if abs(int(p)-int(q))==1] for p in allowed}
    queue=collections.deque((str(p),str(q)) for p in range(8,0,-1) for q in [p-1,p+1] if str(q) in allowed)
    revisions=0;arc_start=time.time()
    while queue and all(allowed.values()):
        p,q=queue.popleft();old=allowed[p]
        good=[i for i in old if any(compatible((p,i),(q,j)) for j in allowed[q])]
        if len(good)!=len(old):
            allowed[p]=good;revisions+=1
            for s in neighbours[p]:
                if s!=q:queue.append((s,p))
        if time.time()-last>10:
            print('IMU_ARC_PRUNE',len(cache),{p:len(v) for p,v in allowed.items()},flush=True);last=time.time()
        if time.time()-start>MAX_SECONDS:limited=True;break
    arc_summary=dict(initial=before_counts,remaining={p:len(v) for p,v in allowed.items()},revisions=revisions,
        elapsed_s=time.time()-arc_start,complete=not queue,adjacent_pairs_only=True)
selected=None;partition_results=[]
if limited or not all(allowed.values()):pass
elif WIDE and not ASSEMBLY:
    for split in [4,3,5,2,6]:
        aa={p:[i for i in ids if pools[p][i]['route_side']==('left' if int(p)<=split else 'right')] for p,ids in allowed.items()}
        selected=search(aa,[]) if all(aa.values()) else None
        partition_results.append(dict(left_pin_count=split,found=bool(selected),nodes=nodes,elapsed_s=time.time()-start))
        if selected or limited:break
else:selected=search(allowed,[])
checks=[]
chosen=[] if selected is None else [routes[k] for k in selected]
for a,b in itertools.combinations(chosen,2):
    distance,where=exact_segment_min(a['curve_mm'],b['curve_mm'])
    checks.append(dict(a=a['id'],b=b['id'],minimum_polyline_center_distance_mm=distance,
        surface_gap_mm=distance-1.016,segment_indices=where,status='PASS' if distance>=required else 'FAIL'))
out=dict(status='PASS' if len(chosen)==8 and all(r['status']=='PASS' for r in checks) else 'BLOCKED',
    scope='Eight IMU wires static joint layout; complete fourteen-wire solid, motion, service and anchors still pending',
    source_pool_file=SOURCE.name,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_blend_sha256=data['source_blend_sha256'],
    source_six_wire_sha256=data['source_six_wire_sha256'],routes=chosen,pair_checks=checks,
    search_nodes=nodes,compatibility_pairs=len(cache),time_or_node_limit=limited,partition_results=partition_results,
    best_partial=[routes[k]['id'] for k in best],best_partial_candidates=[list(k) for k in best],
    arc_consistency=arc_summary,search_time_limit_s=MAX_SECONDS,elapsed_s=time.time()-start,
    extra_print_holes=SLOT_PATH,hardware_selection='CANDIDATE_NOT_SELECTED',cut_lengths_released=False,
    limits=['Finite pool search is not a proof of impossibility if no eight-wire selection is found.',
        'Exact polyline segment minima recheck every selected pair after conservative accelerated filtering.',
        'Terminal lateral exit dimensions, actual wire selection/price and crimping remain unqualified.'])
if SLOT_PATH:out['candidate']=data['candidate']
if DIAGNOSE:
    rows=[]
    for pair,r in diagnostics.items():
        a,b=map(tuple,r['candidates'])
        d,where=exact_segment_min(routes[a]['curve_mm'],routes[b]['curve_mm'])
        rows.append(dict(pins=list(pair),**r,best_pair_exact_center_gap_mm=d,
            best_pair_exact_insulation_gap_mm=d-1.016,exact_segment_indices=where))
    out['pair_diagnostics']=rows
    out['diagnostic_scope']='Only pairs visited by CSP, not exhaustive all-pair feasibility; best candidate means maximal tested coarse gap'
(HERE/(OUT_STEM+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('IMU_JOINT_RESULT',out['status'],nodes,len(cache),len(chosen),out['elapsed_s'],flush=True)
