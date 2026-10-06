"""Find a connected local route around CAM1's fixed rising segment.

Only CAM2 recipe parameters change while the bridge is held 2 mm rearward.
This candidate is not a full-body assembly approval.
"""
from pathlib import Path
SECOND16_SCRIPT = Path(__file__).resolve()
SECOND16_HELPER = SECOND16_SCRIPT.parent/'merge_shell16_back20_wires.py'
__file__ = str(SECOND16_HELPER)
exec(compile(SECOND16_HELPER.read_text().split('\nfor k in range(21):', 1)[0],
             str(SECOND16_HELPER), 'exec'), globals())
__file__ = str(SECOND16_SCRIPT)
import heapq
OUT = ORDER_OUT/'shell16_second_wire_detour'
OUT.mkdir(exist_ok=True)
baseline_path = ORDER_OUT/'shell16_back20_merged/screen.json'
baseline = json.loads(baseline_path.read_text())
assert baseline['script_sha256'] == sha(SECOND16_HELPER)
parameters = {int(p):dict(q) for p,q in baseline['records'][-1]['parameters'].items()}
parameters[4].update(entry_azimuth_deg=-7.5, planar_radius_mm=8.)
set_pose(-2.)
fixed_curves = {}
for pin in [1,3,4]:
    fixed_curves[pin], f = one(pin, parameters[pin])
    assert f is None, f
radius_values = [7.,8.,10.,12.,14.]
cache = {}; reject = Counter(); edge_cache = {}; saved = {}


def params_for(state):
    return dict(parameters[2], entry_azimuth_deg=105.+7.5*state[0],
                planar_radius_mm=radius_values[state[1]], elevation_fraction=state[2]/20.)


def configuration(p):
    key = tuple(round(p[k], 8) for k in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction'])
    if key not in cache:
        c, f = variant_curve(2,p['entry_azimuth_deg'],p['planar_radius_mm'],p['family'],p['elevation_fraction'])
        pair_rows = []
        if not f:
            curves = {**fixed_curves,2:c}
            pair_rows, f = mutual_check(curves)
        if not f:
            lengths[1]['curve_chord_error_mm'] = c['curve_chord_error_mm']
            f = wire_check(2,c['points'],matrices) or self_check(c) or rigid_check(make_terminal(c,bt),matrices)
        if not f:
            f = terminal_checks(curves,bt)
        if f:
            reject[f['kind']+':'+str(f.get('obstacle',str(f.get('a',''))+'/'+str(f.get('b',''))))] += 1
        cache[key] = (c,f,pair_rows)
    return cache[key]


def edge(a,b):
    key = (a,b)
    if key not in edge_cache:
        p0,p1 = params_for(a),params_for(b)
        previous = configuration(p0)[0]
        rows = []; fail = None
        for u in [.25,.5,.75,1.]:
            p = blend_parameters(p0,p1,u)
            c,fail,pair_rows = configuration(p)
            if fail: break
            if np.max(np.abs(np.asarray(c['planar_angles_rad'])-np.asarray(previous['planar_angles_rad'])))>math.pi:
                fail = dict(kind='arc_branch_jump');break
            rows.append((p,c,pair_rows)); previous=c
        edge_cache[key]=(fail,rows)
    return edge_cache[key]


start=(0,0,20); parents={start:None}; costs={start:0}; queue=[(0.,0,start)]; expanded=0; goal=None
c,f,pairs=configuration(params_for(start));assert not f,f
while queue and expanded<700:
    _,depth,state=heapq.heappop(queue)
    if depth != costs[state]:continue
    expanded += 1
    if state[2]<=12:
        goal=state;break
    successors=[]
    for axis in range(3):
        for delta in [-1,1]:
            q=list(state);q[axis]+=delta;q=tuple(q)
            if not(-6<=q[0]<=6 and 0<=q[1]<len(radius_values) and 0<=q[2]<=20):continue
            successors.append(q)
    for q in successors:
        if costs.get(q,10**9)<=depth+1:continue
        f,_=edge(state,q)
        if f:continue
        costs[q]=depth+1;parents[q]=state
        score=depth+1+1.5*max(0,q[2]-12)
        heapq.heappush(queue,(score,depth+1,q))
    if expanded%50==0:
        print('SECOND_DETOUR_PROGRESS',expanded,len(cache),len(queue),round(time.time()-started,1),flush=True)

nodes=[];records=[]
if goal is not None:
    n=goal
    while n is not None:nodes.append(n);n=parents[n]
    nodes.reverse()
    c,f,pairs=configuration(params_for(start))
    route=[(params_for(start),c,pairs)]
    for a,b in zip(nodes,nodes[1:]):
        fail,rows=edge(a,b);assert not fail;route+=rows
    for i,(p,c,pairs) in enumerate(route):
        for pin,q in {**fixed_curves,2:c}.items():saved[f'pin{pin}_pose{i}']=q['points']
        records.append(dict(index=i,parameters=p,pairs=pairs,stock_mm=c['stock_mm'],
                            analytic_total_mm=c['analytic_total_mm'],angles_rad=c['planar_angles_rad']))
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if goal is not None else 'BLOCKED',scope='Finite connected CAM2 detour at one held body pose',
    script_sha256=sha(SECOND16_SCRIPT),helper_sha256=sha(SECOND16_HELPER),
    source_files={str(baseline_path.relative_to(PROJECT)):sha(baseline_path),**baseline['source_files']},
    protected_sources=protected,fixed_parameters=parameters,bridge_y_mm=-2.,bridge_z_mm=18.,
    expanded_nodes=expanded,configurations=len(cache),rejects=dict(reject),nodes=nodes,records=records,
    curves_sha256=sha(OUT/'curves.npz'),wire_OD_mm=OD,clearance_mm=MARGIN,
    full_nominal_lengths_preserved=True,arc_branch_guard=True,continuous_motion='NOT_TESTED',
    whole_back20='NOT_TESTED',complete_attached_assembly='BLOCKED',main_applied=False,
    manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SECOND_DETOUR_DONE',report['status'],expanded,len(records),nodes,dict(reject),flush=True)
