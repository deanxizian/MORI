"""Bounded coupled tilt/offset entry search for the existing rigid link."""
from pathlib import Path
import sys,json,heapq,time
HERE=Path(__file__).resolve().parent
helper=(HERE/'reaction_link_entry_study.py').read_text().split('trials=[]')[0]
exec(compile(helper,str(HERE/'reaction_link_entry_study.py'),'exec'),globals())

start_time=time.monotonic();cache={};tests=0
pivot_z=170.0;clearance=.15

def matrix(state):
    iy,iz,ia=state
    return Matrix.Translation((0,iy*.5,iz*.5)) @ transform('X',ia,pivot_z)

def free_state(state):
    global tests
    if state in cache:return cache[state]
    iy,iz,ia=state
    if not(-20<=iy<=20 and 0<=iz<=220 and -25<=ia<=25):return False
    tests+=1
    m=combined.transform(np.array(matrix(state))[:3,:])
    ok=not hit(m,fixture,.001) and m.min_gap(fixture,1.0)>=clearance
    cache[state]=ok
    return ok

start=(0,0,0);queue=[(0,0,start)];cost={start:0};parent={start:None};found=None
directions=[(0,1,0),(1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(0,-1,0)]
while queue and tests<30000:
    _,g,s=heapq.heappop(queue)
    if g!=cost[s]:continue
    if s[1]>=200:found=s;break
    for d in directions:
        t=tuple(a+b for a,b in zip(s,d))
        ng=g+(1 if d[1] else 1.05)
        if ng>=cost.get(t,1e12) or not free_state(t):continue
        cost[t]=ng;parent[t]=s
        # A weighted search favors removal progress; failure is not a
        # completeness proof over untested offsets or rotations.
        score=ng+1.25*(200-t[1])+abs(t[0])*.02+abs(t[2])*.02
        heapq.heappush(queue,(score,ng,t))
    if tests and tests%1000==0:
        print('LINK_SEARCH',tests,'reachable',len(cost),'highest_lift',max(x[1] for x in cost)*.5,flush=True)

path=[];refined=[];hits=[];gaps=[]
if found:
    s=found
    while s is not None:path.append(s);s=parent[s]
    path.reverse()
    for a,b in zip(path,path[1:]):
        for t in np.linspace(0,1,5):
            st=np.array(a)*(1-t)+np.array(b)*t;tr=matrix(st)
            m=combined.transform(np.array(tr)[:3,:]);v=hit(m,fixture,.001);gap=m.min_gap(fixture,2)
            row=dict(y_offset_mm=float(st[0]*.5),z_offset_mm=float(st[1]*.5),tilt_x_deg=float(st[2]),matrix=np.array(tr).tolist())
            if v or gap<clearance-.00001:hits.append(dict(**row,overlap_mm3=v,gap_mm=gap))
            refined.append(row);gaps.append(gap)
out=dict(status='PASS' if found and not hits else 'BLOCKED',source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 main_applied=False,fixture=['Pitch_Yoke'],moving=movers,pivot_z_mm=pivot_z,
 tested_states=tests,reachable_states=len(cost),elapsed_s=time.monotonic()-start_time,
 maximum_reached_lift_mm=max(x[1] for x in cost)*.5,required_sampled_gap_mm=clearance,
 minimum_path_gap_mm=min(gaps) if gaps else None,path=refined,refinement_failures=hits,
 limits=['Finite path sampling; no global impossibility or continuous-motion proof',
         'Detached bare yoke before servos; horn/fastener envelopes are still provisional',
         'No geometry changes or assembly approval; physical grip/preload not qualified'])
(HERE/'reaction_link_path_search.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('LINK_PATH_FINAL',out['status'],'tests',tests,'lift',out['maximum_reached_lift_mm'],'min_gap',out['minimum_path_gap_mm'],flush=True)
