"""Necessary wire-length bounds for the six saved bare-plug approach paths.

The bounds include both declared 5 mm straight exits and the distance between
their ends. Passing is not a curvature/obstacle or flexible-installation proof.
Failure rejects that endpoint configuration for the current nominal length.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,heapq
import numpy as np
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3];A2=A8.parent/'harness_A2'
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'later_connections/length_budget';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
path_file=BASE/'later_connections/grid_margin_approach/screen.json'
paths=read(path_file);pr={r['port']:r for r in paths['rows']}
route_files=[A2/'ecowire_joint.json',A2/'imu_axial_complete_joint_diagnostic.json']
routes=[r for p in route_files for r in read(p)['routes'] if r['harness'] in ['H01','H02','H04']]
grouped={g:[r for r in routes if r['harness']==g] for g in ['H01','H02','H04']}

def length_reference(row):
    if 'controls_mm' in row:
        p=np.array(row['controls_mm']);R=row['analytic_bend_radius_mm']
        length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())+2*row['terminal_straight_mm']
        for a,b,c in zip(p,p[1:],p[2:]):
            u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
            angle=math.acos(np.clip(u@v,-1,1))
            length+=R*(angle-2*math.tan(angle/2))
        return length,0.,'Analytic line and circular-arc length from the existing route controls'
    values=[]
    for n in [64,128]:
        nodes,weights=np.polynomial.legendre.leggauss(n);t=(nodes+1)/2
        total=2*row['terminal_straight_mm']
        for control in row['cubic_controls_mm']:
            c=np.array(control);v=3*((1-t)[:,None]**2*(c[1]-c[0])+2*((1-t)*t)[:,None]*(c[2]-c[1])+t[:,None]**2*(c[3]-c[2]))
            total+=float(np.sum(weights*np.linalg.norm(v,axis=1))/2)
        values.append(total)
    return values[-1],abs(values[1]-values[0]),'64/128-point Gaussian quadrature agreement only; not a certified integral error bound'

def samples(port,n=81):
    points=np.asarray(pr[port]['path_translations_mm']);s=np.r_[0,np.linalg.norm(np.diff(points,axis=0),axis=1).cumsum()]
    t=np.linspace(0,s[-1],n)
    return np.array([np.interp(t,s,points[:,k]) for k in range(3)]).T

budgets={r['id']:length_reference(r) for r in routes}
rows=[]
for group,items in grouped.items():
    a,b=items[0]['from_port'],items[0]['to_port'];A=samples(a);B=samples(b)
    axa=np.asarray(pr[a]['initial_axis']);axb=np.asarray(pr[b]['initial_axis'])
    bounds=[]
    for r in items:
        p=np.array(r['curve_mm']);straight=r['terminal_straight_mm'];L,err,method=budgets[r['id']]
        left=p[0]+straight*axa;right=p[-1]+straight*axb
        distance=np.linalg.norm(left+A[:,None,:]-right-B[None,:,:],axis=2)+2*straight
        slack=L-distance;bounds.append(slack)
    min_slack=np.minimum.reduce(bounds)
    legal=min_slack>=0
    # Endpoint progress grid only. Edges between samples are not certified for
    # material, and the actual wire still has to avoid all robot geometry.
    n=len(A);parents={(0,0):None};queue=[(0.,(0,0))];cost={(0,0):0.};end=None
    while queue:
        g,state=heapq.heappop(queue)
        if state==(n-1,n-1):end=state;break
        i,j=state
        for di,dj in [(1,1),(1,0),(0,1)]:
            q=(i+di,j+dj)
            if q[0]>=n or q[1]>=n or not legal[q]:continue
            new=g+math.hypot(di,dj)
            if new>=cost.get(q,math.inf):continue
            cost[q]=new;parents[q]=state;heapq.heappush(queue,(new,q))
    coordination=[]
    if end:
        while end is not None:coordination.append(list(end));end=parents[end]
        coordination.reverse()
    info=[]
    for r,slack in zip(items,bounds):
        L,err,method=budgets[r['id']]
        info.append(dict(id=r['id'],existing_polyline_length_mm=r['geometric_centerline_length_mm'],
            refined_reference_length_mm=L,quadrature_disagreement_mm=err,length_method=method,
            from_only_worst_margin_mm=float(slack[:,0].min()),to_only_worst_margin_mm=float(slack[0,:].min()),
            simultaneous_exterior_margin_mm=float(slack[-1,-1]),
            from_exterior_minimum_length_mm=L-float(slack[-1,0]),
            to_exterior_minimum_length_mm=L-float(slack[0,-1]),
            both_exterior_minimum_length_mm=L-float(slack[-1,-1])))
    rows.append(dict(harness=group,from_port=a,to_port=b,source_route_count=len(items),wire_rows=info,
        endpoint_progress_samples_per_port=n,
        from_only_status='PASS' if np.all(min_slack[:,0]>=0) else 'BLOCKED',
        to_only_status='PASS' if np.all(min_slack[0,:]>=0) else 'BLOCKED',
        both_exterior_status='PASS' if min_slack[-1,-1]>=0 else 'BLOCKED',
        necessary_length_coordination_status='PASS' if coordination else 'BLOCKED',
        coordination_indices=coordination or None,
        largest_length_deficit_mm=max(0.,-float(min_slack.min())),
        geometry_and_bend_radius='NOT_TESTED'))
out=dict(status='PASS',scope='Necessary endpoint-length audit completed; status is audit completion, not assembly approval',
    script_sha256=sha(SCRIPT),source_files={str(p.relative_to(ROOT)):sha(p) for p in [path_file]+route_files},
    protected_sources=paths['protected_sources'],rows=rows,
    source_lengths='Existing unselected static candidate lengths; not supplier cut lengths and no service allowance added',
    lower_bound='5 mm straight exit at each end plus Euclidean separation of the two straight-leg endpoints',
    interpretation='Negative margin rejects only that endpoint configuration at the current nominal length; positive margin does not prove routing or curvature',
    actual_terminal_exit_geometry='ASSUMED',full_flexible_installation='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    generated_utc=datetime.now(timezone.utc).isoformat())
for p,h in out['protected_sources'].items():assert sha(ROOT/p)==h
(OUT/'audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['harness','from_only_status','to_only_status','both_exterior_status','necessary_length_coordination_status','largest_length_deficit_mm']} for r in rows],ensure_ascii=False))
