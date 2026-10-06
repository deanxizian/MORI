"""Bound curvature and free-tail packing throughout the seating family.

Moving Bezier controls are C_i + w_i*(0, d, H(d)). Their derivative cross
product is affine in that common shift because shift cross itself is zero.
Bernstein convex-hull bounds cover both curve parameter and offset intervals.
"""
from pathlib import Path
import hashlib,json,math,time
import numpy as np
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/aligned_tails'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pool_file=A8/'cam_fan_in/four_bend_transition/pool.json'
pool=json.loads(pool_file.read_text());candidates=[r['candidates'][0] for r in pool['rows']]
finite_file=OUT/'screen.json';finite=json.loads(finite_file.read_text());assert finite['status']=='PASS'
radius=candidates[0]['parameters']['radii_mm'][-1]
delta=candidates[0]['end_mm'][1]-candidates[0]['parameters']['side_y_mm']
def height(d):
    return 2*radius*(math.sin(math.acos(1-(delta+d)/(2*radius)))-math.sin(math.acos(1-delta/(2*radius))))
def split(c):
    levels=[np.array(c)]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2)
    return np.array([p[0] for p in levels]),np.array([p[-1] for p in levels[::-1]])
def bound(c,w,a,b):
    v=3*np.diff(c,axis=0);vw=3*np.diff(w);acc=6*np.diff(c,n=2,axis=0);aw=6*np.diff(w,n=2)
    cb=np.zeros((4,3));cy=cb.copy();cz=cb.copy();ey=np.array([0.,1.,0.]);ez=np.array([0.,0.,1.])
    for i in range(3):
        for j in range(2):
            weight=math.comb(2,i)/math.comb(3,i+j)
            cb[i+j]+=weight*np.cross(v[i],acc[j])
            cy[i+j]+=weight*(aw[j]*np.cross(v[i],ey)+vw[i]*np.cross(ey,acc[j]))
            cz[i+j]+=weight*(aw[j]*np.cross(v[i],ez)+vw[i]*np.cross(ez,acc[j]))
    vv=[];cross=[]
    for d in [a,b]:
        for z in [height(a),height(b)]:
            vv.append(v+vw[:,None]*np.array([0.,d,z]));cross.append(cb+cy*d+cz*z)
    vv=np.concatenate(vv);low=vv.min(0);high=vv.max(0)
    speed=float(np.linalg.norm(np.maximum(np.maximum(low,-high),0.)))
    cmax=float(np.linalg.norm(np.concatenate(cross),axis=1).max())
    return max(0.,speed-1e-12)**3/(cmax*(1+1e-9)+1e-20)
def t_audit(c,w,a,b,depth=0):
    rad=bound(c,w,a,b)
    if rad>=7.:return rad,1,0
    if depth>=12:return rad,1,1
    c1,c2=split(c);w1,w2=split(w)
    r1,n1,u1=t_audit(c1,w1,a,b,depth+1);r2,n2,u2=t_audit(c2,w2,a,b,depth+1)
    return min(r1,r2),n1+n2,u1+u2
started=time.time();rows=[]
for slot,candidate in enumerate(candidates):
    for index,ctrl in enumerate(candidate['controls_mm']):
        c=np.array(ctrl);w=np.zeros(4)
        if index==len(candidate['controls_mm'])-1:w[-2:]=1.
        todo=[(0.,1.5,0)];accepted=[];unresolved=[]
        while todo:
            a,b,depth=todo.pop();r,n,u=t_audit(c,w,a,b)
            if not u:accepted.append(dict(offset_interval_mm=[a,b],minimum_radius_lower_mm=r,curve_intervals=n));continue
            if depth>=12:unresolved.append(dict(offset_interval_mm=[a,b],minimum_radius_lower_mm=r));continue
            mid=(a+b)/2;todo.extend([(mid,b,depth+1),(a,mid,depth+1)])
        accepted.sort(key=lambda r:r['offset_interval_mm'][0])
        covered=bool(accepted and accepted[0]['offset_interval_mm'][0]==0 and accepted[-1]['offset_interval_mm'][1]==1.5
            and all(a['offset_interval_mm'][1]==b['offset_interval_mm'][0] for a,b in zip(accepted,accepted[1:])))
        row=dict(slot=slot,bezier_piece=index,status='PASS' if covered and not unresolved else 'BLOCKED',
            coverage=covered,accepted=accepted,unresolved=unresolved)
        rows.append(row);print('ROOT_RADIUS_SPAN',slot,index,row['status'],len(accepted),flush=True)
alpha_min=math.acos(1-delta/(2*radius));sin_min=math.sin(alpha_min)
height_derivative_bound=math.cos(alpha_min)/sin_min
fan_length_derivative_bound=1/sin_min
circle_position_derivative_bound=3/(2*sin_min)
free_contact_derivative_bound=math.hypot(1,height_derivative_bound+fan_length_derivative_bound)
motion_bound=max(circle_position_derivative_bound,free_contact_derivative_bound)
max_slope=1.8875*1.875/16
free_gap=1/math.sqrt(1+max_slope**2)-finite['wire_OD_mm']
assert motion_bound<3. and free_gap>.3
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='All seating offsets 0..1.5 mm: Bezier curvature, unchanged circular radii, free-tail separation and displacement bounds; no collision result',
    script_sha256=sha(SCRIPT),source_main_sha256=finite['source_main_sha256'],
    source_finite_sha256=sha(finite_file),source_fan_pool_sha256=sha(pool_file),
    required_radius_mm=7.,circular_radius_mm=7.2,bezier_spans=rows,
    root_height_derivative_abs_bound=height_derivative_bound,fan_length_derivative_abs_bound=fan_length_derivative_bound,
    circular_point_displacement_derivative_bound=circle_position_derivative_bound,
    free_contact_displacement_derivative_bound=free_contact_derivative_bound,
    chosen_global_displacement_lipschitz=3.,
    displacement_scope='Same normalized parameter on each exact circle/Bezier/straight span; endpoints, whole centreline sets and nonrotating contacts included',
    free_free_gap_lower_bound_mm=free_gap,free_free_scope='Four identical translated X(Z) quintics, 1-mm X spacing, maximum slope bound; unequal final straight lengths are subsets of the same extended curves',
    continuous_collision='NOT_TESTED',physical_bend_life='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'math_bounds.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('ROOT_SEATING_MATH',report['status'],free_gap,round(time.time()-started,2),flush=True)
