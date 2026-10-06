"""Refine existing link entry at 0.25 mm/0.25 deg, allowing coupled steps."""
from pathlib import Path
import sys, json, heapq, itertools, time
HERE = Path(__file__).resolve().parent
helper = (HERE / 'reaction_bench_order.py').read_text().split('rows = []')[0]
exec(compile(helper, str(HERE / 'reaction_bench_order.py'), 'exec'), globals())

pivot_z = 170.
required_gap = .15
steps = [x for x in itertools.product([-1, 0, 1], repeat=3) if any(x)]

def matrix(state):
    iy, iz, ia = state
    return (Matrix.Translation((0, iy*.25, iz*.25)) @
            Matrix.Translation((0, 0, pivot_z)) @
            Matrix.Rotation(math.radians(ia*.25), 4, 'X') @
            Matrix.Translation((0, 0, -pivot_z)))

def solve(name, moving):
    cache = {}; tested = 0; started = time.monotonic()
    def clear(s):
        nonlocal tested
        if s in cache: return cache[s]
        iy, iz, ia = s
        if not(-16 <= iy <= 16 and 0 <= iz <= 400 and -40 <= ia <= 40): return False
        tested += 1
        m = moving.transform(np.array(matrix(s))[:3, :])
        v = hit(m, fixture, .001)
        gap = 0 if v else m.min_gap(fixture, 1)
        ok = not v and gap >= required_gap
        cache[s] = ok
        return ok
    start = (0, 0, 0)
    assert clear(start)
    heap = [(0., 0., start)]; costs = {start: 0.}; parent = {start: None}
    found = None; best = start; last_report = 0
    while heap and tested < 35000:
        _, g, s = heapq.heappop(heap)
        if g != costs[s]: continue
        if s[1] > best[1]: best = s
        if s[1] >= 360: found = s; break
        for step in steps:
            t = tuple(a+b for a,b in zip(s,step))
            ng = g + math.sqrt(sum(x*x for x in step))
            if ng >= costs.get(t, 1e20) or not clear(t): continue
            costs[t] = ng; parent[t] = s
            priority = ng + 1.5*(360-t[1]) + abs(t[0])*.02 + abs(t[2])*.02
            heapq.heappush(heap, (priority, ng, t))
        if tested > last_report + 2500:
            print('REFINED',name,tested,'reachable',len(costs),'maxlift',best[1]*.25,flush=True)
            last_report = tested
    path=[];s=found if found is not None else best
    while s is not None: path.append(s);s=parent[s]
    path.reverse()
    bad=[];gaps=[];refined=[]
    for a,b in zip(path,path[1:]):
        for t in np.linspace(0,1,5):
            st=np.array(a)*(1-t)+np.array(b)*t
            tr=matrix(st);m=moving.transform(np.array(tr)[:3,:]);v=hit(m,fixture,.001)
            gap=0 if v else m.min_gap(fixture,2)
            row=dict(y_mm=float(st[0]*.25),z_mm=float(st[1]*.25),tilt_x_deg=float(st[2]*.25))
            if v or gap<required_gap-1e-6:bad.append(dict(**row,overlap_mm3=v,gap_mm=gap))
            gaps.append(gap);refined.append(row)
    return dict(moving=name,status='PASS' if found and not bad else 'BLOCKED',
        termination='found' if found else 'search_limit' if tested>=35000 else 'bounded_reachable_set_exhausted',
        tested_states=tested,reachable_states=len(costs),elapsed_s=time.monotonic()-started,
        maximum_reached_lift_mm=best[1]*.25,minimum_sampled_path_gap_mm=min(gaps) if gaps else None,
        best_or_complete_path=refined,path_recheck_failures=bad)

results=[]
for label, geometry in [('bare_link',bare),('preassembled_link_horn_clamp',preassembled)]:
    r=solve(label,geometry);results.append(r)
    print('REFINED_RESULT',label,r['status'],r['tested_states'],r['maximum_reached_lift_mm'],flush=True)
out=dict(revision=P['revision'],source_blend_sha256=before,source_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==before,
    status='PASS' if all(r['status']=='PASS' for r in results) else 'BLOCKED',main_applied=False,
    required_sampled_gap_mm=required_gap,translation_grid_mm=.25,tilt_grid_deg=.25,pivot_z_mm=pivot_z,
    results=results,scope='Refined existing-part bench insertion; y offset, z lift and X tilt with diagonal graph steps',
    limits=['Finite local search, not a proof against all 6-DOF paths','Bare link omits fasteners only as an explicit bench sequence test',
            'Final horn dimensions and physical manipulation remain unqualified','No model geometry, hardware or assumptions altered'])
(HERE/'reaction_refined_path.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('REFINED_FINAL',out['status'],flush=True)
