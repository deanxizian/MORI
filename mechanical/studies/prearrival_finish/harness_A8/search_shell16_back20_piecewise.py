"""Bounded piecewise control search for the three blocked CAM leads.

Individual wires only. Nodes preserve the saved circle family and full
nominal material. Every graph edge includes intermediate sample checks;
neither unsampled clearance nor four-wire packing is certified here.
"""
from pathlib import Path
GRAPH16_SCRIPT=Path(__file__).resolve();GRAPH16_HELPER=GRAPH16_SCRIPT.parent/'screen_shell16_back20_wire_families.py'
__file__=str(GRAPH16_HELPER)
exec(compile(GRAPH16_HELPER.read_text().split('\npools={};results=',1)[0],str(GRAPH16_HELPER),'exec'),globals())
__file__=str(GRAPH16_SCRIPT)
import heapq
OUT=ORDER_OUT/'shell16_back20_piecewise';OUT.mkdir(exist_ok=True)
END_PATH=ORDER_OUT/'shell16_back20_wire_families/screen.json'
end_report=json.loads(END_PATH.read_text())
assert end_report['script_sha256']==sha(GRAPH16_HELPER)
node_limit=1500;results=[];saved={};radii=[7.,8.,10.,12.,14.,18.]

for pin in [3,1,2]:
    base=starts[pin];cache={};rejects=Counter();edge_cache={};clock0=time.time()
    initial=(0,0,radii.index(base['planar_radius_mm']),round(4*base['elevation_fraction']))
    assert initial[1]==0

    def parameters(node):
        return dict(entry_azimuth_deg=base['entry_azimuth_deg']+7.5*node[1],
                    planar_radius_mm=radii[node[2]],family=base['family'],elevation_fraction=node[3]/4.)

    def eval_at(back,p):
        set_pose(-float(back));return one(pin,p)

    def node_curve(node):
        if node not in cache:
            c,f=eval_at(node[0],parameters(node))
            cache[node]=(c,f)
            if f:rejects[f['kind']+(':'+f['obstacle'] if 'obstacle' in f else '')]+=1
        return cache[node]

    c0,f0=node_curve(initial);assert f0 is None
    assert np.array_equal(c0['points'],start_curves[f'pin{pin}_pose36'])

    def edge(a,b):
        key=(a,b)
        if key in edge_cache:return edge_cache[key]
        c,f=node_curve(b)
        if f:edge_cache[key]=f;return f
        pa=parameters(a);pb=parameters(b);previous=np.asarray(node_curve(a)[0]['planar_angles_rad'])
        for t in [.25,.5,.75,1.]:
            p={k:(1-t)*pa[k]+t*pb[k] for k in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']}
            p['family']=base['family']
            q,f=eval_at((1-t)*a[0]+t*b[0],p) if t<1. else (c,None)
            if f:break
            angles=np.asarray(q['planar_angles_rad'])
            if np.max(np.abs(angles-previous))>math.pi:
                f=dict(kind='arc_branch_jump',pin=pin);break
            previous=angles
        edge_cache[key]=f
        return f

    queue=[(20.,0.,initial)];best={initial:0.};parent={};expanded=0;furthest=0;goal_node=None
    while queue and expanded<node_limit:
        _,cost,node=heapq.heappop(queue)
        if cost>best.get(node,math.inf)+1e-9:continue
        expanded+=1;furthest=max(furthest,node[0])
        if node[0]==20:goal_node=node;break
        neighbours=[(node[0]+1,*node[1:])]
        # Parameter changes occur while both rigid assemblies are held still.
        for axis in [1,2,3]:
            for step in [-1,1]:
                q=list(node);q[axis]+=step
                if -8<=q[1]<=8 and 0<=q[2]<len(radii) and 0<=q[3]<=4:neighbours.append(tuple(q))
        for q in neighbours:
            stepcost=1. if q[0]!=node[0] else .24
            newcost=cost+stepcost
            if newcost>=best.get(q,math.inf)-1e-9:continue
            if edge(node,q):continue
            best[q]=newcost;parent[q]=node
            heapq.heappush(queue,(newcost+(20-q[0]),newcost,q))
        if expanded%100==0:
            print('SHELL16_PIECEWISE_PROGRESS',pin,expanded,'furthest',furthest,'cached',len(cache),round(time.time()-clock0,2),flush=True)
    selected=[];check_rows=[]
    if goal_node:
        node=goal_node
        while True:
            selected.append(node)
            if node==initial:break
            node=parent[node]
        selected.reverse()
        for edge_index,(a,b) in enumerate(zip(selected,selected[1:])):
            pa=parameters(a);pb=parameters(b)
            for t in ([0.,.25,.5,.75,1.] if edge_index==0 else [.25,.5,.75,1.]):
                p={k:(1-t)*pa[k]+t*pb[k] for k in ['entry_azimuth_deg','planar_radius_mm','elevation_fraction']};p['family']=base['family']
                back=(1-t)*a[0]+t*b[0];c,f=eval_at(back,p);assert f is None
                i=len(check_rows);saved[f'pin{pin}_pose{i}']=c['points']
                check_rows.append(dict(index=i,bridge_y_mm=-back,bridge_z_mm=18.,parameters=p,
                    analytic_total_mm=c['analytic_total_mm'],sampled_total_mm=c['sampled_total_mm'],
                    stock_mm=c['stock_mm'],curve_chord_error_mm=c['curve_chord_error_mm'],planar_angles_rad=c['planar_angles_rad']))
    row=dict(pin=pin,status='PASS' if goal_node else 'BLOCKED',expanded_nodes=expanded,cached_nodes=len(cache),
             node_limit=node_limit,furthest_rearward_mm=furthest,bounded_search_exhausted=not queue and not goal_node,
             queue_remaining=len(queue),rejections=dict(rejects),selected_nodes=selected,selected_rows=check_rows,
             individual_only=True,elapsed_s=time.time()-clock0)
    results.append(row)
    print('SHELL16_PIECEWISE_PIN_DONE',pin,row['status'],expanded,furthest,round(time.time()-clock0,2),flush=True)
    # The first wire is the most constrained. If its local component is
    # exhausted, retain that diagnostic rather than repeating it for others.
    if pin==3 and goal_node is None:break
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if len(results)==3 and all(r['status']=='PASS' for r in results) else 'BLOCKED',
    scope='Individual finite piecewise paths only; other CAM wires are not obstacles in this search',
    script_sha256=sha(GRAPH16_SCRIPT),helper_sha256=sha(GRAPH16_HELPER),
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [END_PATH,rigid_path,JOINT/'screen.json',JOINT/'verification.json',JOINT/'curves.npz',JOINT/'wire_solids.json']},
    protected_sources=protected,results=results,curves_sha256=sha(OUT/'curves.npz'),
    full_nominal_lengths_preserved=True,wire_families_unchanged=True,mutual_packing='NOT_TESTED',
    continuous_motion='NOT_TESTED',complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_PIECEWISE_DONE',report['status'],flush=True)
