"""Bounded translation search for J18 after CAM lines, before body shells.

Each grid edge is an exact swept axis-aligned housing box. Nine other upper
wire candidates and fourteen fixed-body wire solids remain. This is a housing
approach study: J18's own attached wires and mating contact are unresolved.
"""
from pathlib import Path
import collections,heapq,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_plug_search';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from upper_pack_geometry import refined

ctx=Context();started=time.time();key='power_J18';plug=ctx.plug[key]
assert np.allclose(ctx.port_pins[key]['axis'],[0,0,1])
deferred={'Body_Upper','Body_Lower'}
targets={n:t for n,t in ctx.targets.items() if n not in deferred|{'Plug_'+key}}
names=list(targets);los=np.array([targets[n]['lo'] for n in names]);his=np.array([targets[n]['hi'] for n in names])
curvefile=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(curvefile);wires={}
for name in [*[f'CAM_{i}' for i in range(1,5)],'P_J9_1','P_J9_2','P_J9_3','SPK_reservation_3','SPK_reservation_6']:
    p=refined(curves[name+'_y0'+('_p0' if name.startswith('CAM_') else '')],.02)
    rad=.3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842
    wires[name]=dict(p=p,radius=rad,error=.0003,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),lo=p.min(0),hi=p.max(0))
calls=0;obstacles=collections.Counter();cache={};min_gap=.301
def clear(a,b,mate=False):
    global calls,min_gap
    calls+=1;lo=plug.lo+np.minimum(a,b);hi=plug.hi+np.maximum(a,b)
    m=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
    ids=np.flatnonzero(np.all(lo<=his+.301,axis=1)&np.all(hi+.301>=los,axis=1))
    for i in ids:
        name=names[i]
        if mate and name=='Power_Module':continue
        target=targets[name]['m'];vol=float((m^target).volume());gap=float(m.min_gap(target,.301)) if abs(vol)<1e-7 else 0.
        if abs(vol)>1e-6 or gap<.3:
            obstacles[name]+=1;return dict(target=name,overlap_mm3=vol,gap_mm=gap)
    for name,w in wires.items():
        bound=w['radius']+.3+w['step']/2+w['error']+1e-4
        if not(np.all(lo<=w['hi']+bound) and np.all(hi+bound>=w['lo'])):continue
        ids=np.flatnonzero(np.all(w['p']>=lo-bound,axis=1)&np.all(w['p']<=hi+bound,axis=1))
        if len(ids)==0:continue
        p=w['p'][ids];d=np.linalg.norm(np.maximum(np.maximum(lo-p,p-hi),0.),axis=1);k=int(np.argmin(d))
        if d[k]<bound:
            obstacles['wire_'+name]+=1;return dict(target='wire_'+name,point_mm=p[k].tolist(),gap_lower_bound_mm=float(d[k]-bound+.3))
    return None

# Initial 12 mm release checks all other candidates. The intended mating
# board is separated as an unresolved interface, not a qualified contact.
initial=[]
for z in np.arange(0,12,.5):
    hit=clear(np.array([0,0,z]),np.array([0,0,z+.5]),mate=True)
    initial.append(dict(z_mm=float(z),hit=hit))
    if hit:break
start=(0,0,6);target_y=45;previous={};cost={start:0};queue=[];counter=itertools.count();end=None;popped=0
heapq.heappush(queue,(1.25*target_y,next(counter),start))
bounds=((-25,25),(-3,45),(3,16));node_limit=5000;time_limit=100.
if not any(r['hit'] for r in initial):
 while queue and popped<node_limit and time.time()-started<time_limit:
    _,_,node=heapq.heappop(queue);popped+=1
    if node[1]>=target_y:end=node;break
    for delta in [(0,1,0),(0,0,1),(-1,0,0),(1,0,0),(0,0,-1),(0,-1,0)]:
        nxt=tuple(a+b for a,b in zip(node,delta))
        if not all(lo<=v<=hi for v,(lo,hi) in zip(nxt,bounds)):continue
        newcost=cost[node]+1
        if newcost>=cost.get(nxt,float('inf')):continue
        edge=tuple(sorted([node,nxt]))
        if edge not in cache:cache[edge]=clear(np.array(node)*2.,np.array(nxt)*2.)
        if cache[edge] is not None:continue
        cost[nxt]=newcost;previous[nxt]=node
        heapq.heappush(queue,(newcost+1.25*max(0,target_y-nxt[1]),next(counter),nxt))
    if popped%100==0:print('POWER_PLUG_SEARCH_PROGRESS',popped,len(cache),time.time()-started,flush=True)
path=[]
if end:
    node=end
    while True:
        path.append(np.array(node,float)*2.)
        if node==start:break
        node=previous[node]
    path=path[::-1];np.savez_compressed(OUT/'path.npz',shifts_mm=np.vstack([np.zeros(3),path]),plug_vertices_mm=plug.v,plug_triangles=plug.f)
ctx.assert_unchanged()
r=dict(status='PASS' if end else 'BLOCKED',scope='Bounded J18 housing approach after nine upper candidates, before two body shells; not complete wired installation',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [curvefile,HERE/'upper_pack_geometry.py',HERE/'check_cam_power_side_access.py',BASE/'cam_restraints/power_side_access/review.json']},
    initial_axial_release=initial,deferred_parts=sorted(deferred),retained_upper_wires=list(wires),retained_fixed_wire_solids=14,
    search=dict(grid_mm=2,bounds_grid=bounds,node_limit=node_limit,time_limit_s=time_limit,popped=popped,edges_checked=len(cache),collision_queries=calls,weighted_A_star=1.25,optimality_claim=False,obstacles=dict(obstacles)),
    path_shifts_mm=[p.tolist() for p in path],continuous_translation='PASS for successful path edges' if end else 'BLOCKED',
    nominal_housing_bounds_mm=np.r_[plug.lo,plug.hi].tolist(),mating_interface='BLOCKED',attached_J18_wires='NOT_TESTED',complete_sequence='BLOCKED',
    main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    path_sha256=sha(OUT/'path.npz') if end else None,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('POWER_PLUG_SEARCH_DONE',r['status'],popped,len(path),r['elapsed_s'],flush=True)
