"""Whole-family curvature, displacement and packing bounds for recovery.

Bezier controls are affine in recovery fraction f and monotone H(1.8-.3f).
Independent f/H rectangles enclose the family; Bernstein derivative hulls
then bound speed and cross products over each curve span. This is separate
from the finite-pose collision checker and does not alter CAD.
"""
from pathlib import Path
import hashlib,json,math,time
import numpy as np
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/ordered_feed_recovery'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pool_path=A8/'cam_fan_in/four_bend_transition/pool.json'
pool=json.loads(pool_path.read_text());candidates=[r['candidates'][0] for r in pool['rows']]
finite_path=OUT/'screen.json';finite=json.loads(finite_path.read_text());assert finite['status']=='PASS'
c0=candidates[0];r=c0['parameters']['radii_mm'][-1]
dy=c0['end_mm'][1]-c0['parameters']['side_y_mm']
def height(d):return 2*r*(math.sin(math.acos(1-(dy+d)/(2*r)))-math.sin(math.acos(1-dy/(2*r))))
def split(c):
    levels=[np.array(c)]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2.)
    return np.array([p[0] for p in levels]),np.array([p[-1] for p in levels[::-1]])
def radius_bound(c,df,dh,a,b):
    controls=np.array([c+f*df+h*dh for f in [a,b] for h in [height(1.8-.3*b),height(1.8-.3*a)]])
    v=3*np.diff(controls,axis=1);acc=6*np.diff(controls,n=2,axis=1)
    flat=v.reshape(-1,3);lo=flat.min(0);hi=flat.max(0)
    speed=float(np.linalg.norm(np.maximum(np.maximum(lo,-hi),0.)))
    crosslo=np.zeros((4,3));crosshi=np.zeros((4,3))
    for i in range(3):
        for j in range(2):
            weight=math.comb(2,i)*math.comb(1,j)/math.comb(3,i+j)
            x=np.cross(v[:,i,None,:],acc[None,:,j,:]).reshape(-1,3)
            crosslo[i+j]+=weight*x.min(0);crosshi[i+j]+=weight*x.max(0)
    maximum=float(np.linalg.norm(np.maximum(abs(crosslo),abs(crosshi)),axis=1).max())
    return max(0.,speed-1e-12)**3/(maximum*(1+1e-9)+1e-20)
def audit_u(c,df,dh,a,b,depth=0):
    radius=radius_bound(c,df,dh,a,b)
    if radius>=7.:return radius,1,0
    if depth>=11:return radius,1,1
    cl,cr=split(c);fl,fr=split(df);hl,hr=split(dh)
    p=audit_u(cl,fl,hl,a,b,depth+1);q=audit_u(cr,fr,hr,a,b,depth+1)
    return min(p[0],q[0]),p[1]+q[1],p[2]+q[2]
started=time.time();rows=[];bezier_motion=[];bezier_length=[]
alpha_y_min=math.acos(1-(dy+1.5)/(2*r))
Hprime=.3*math.cos(alpha_y_min)/math.sin(alpha_y_min)
for slot,candidate in enumerate(candidates):
    for index,ctrl in enumerate(candidate['controls_mm']):
        c=np.array(ctrl);df=np.zeros_like(c);dh=np.zeros_like(c)
        if index==len(candidate['controls_mm'])-1:
            c[-2:]+=np.array([.2,1.8,0.]);df[-2:]=[-.2,-.3,0.];dh[-2:,2]=1.
            if slot==3:c[-2,0]+=.5;df[-2,0]-=.5
        # H' is negative. Corners of its interval bound all control speeds
        # and the integral of their derivative polygon for arclength speed.
        derivs=np.array([df,df-Hprime*dh])
        bezier_motion.append(float(np.linalg.norm(derivs,axis=2).max()))
        bezier_length.append(float(np.linalg.norm(np.diff(derivs,axis=1),axis=2).sum(axis=1).max()))
        todo=[(float(a),float(b),0) for a,b in zip(np.linspace(0,1,33),np.linspace(0,1,33)[1:])]
        accepted=[];unresolved=[]
        while todo:
            a,b,depth=todo.pop();rad,n,u=audit_u(c,df,dh,a,b)
            if not u:accepted.append(dict(fraction_interval=[a,b],minimum_radius_lower_mm=rad,curve_intervals=n));continue
            if depth>=8:unresolved.append(dict(fraction_interval=[a,b],minimum_radius_lower_mm=rad));continue
            mid=(a+b)/2.;todo.extend([(mid,b,depth+1),(a,mid,depth+1)])
        accepted.sort(key=lambda x:x['fraction_interval'][0])
        covered=bool(accepted and accepted[0]['fraction_interval'][0]==0. and accepted[-1]['fraction_interval'][1]==1. and all(p['fraction_interval'][1]==q['fraction_interval'][0] for p,q in zip(accepted,accepted[1:])))
        rows.append(dict(slot=slot,piece=index,status='PASS' if covered and not unresolved else 'BLOCKED',accepted=accepted,unresolved=unresolved))
        print('RECOVERY_RADIUS',slot,index,rows[-1]['status'],len(accepted),round(time.time()-started,1),flush=True)
par=c0['parameters'];dx0=c0['end_mm'][0]-par['side_x_mm'];rx=par['radii_mm'][2]
alpha_x_min=math.acos(1-dx0/(2*rx))
circle_point=1.5*.2/math.sin(alpha_x_min)+1.5*.3/math.sin(alpha_y_min)
root_speed=math.sqrt(.2**2+.3**2+Hprime**2)
circle_length=.2/math.sin(alpha_x_min)+.3/math.sin(alpha_y_min)+circle_point+root_speed
fan_speed=max(circle_point,root_speed,*bezier_motion)
fan_length_speed=max(circle_length,sum(bezier_length[:2]),sum(bezier_length[2:4]),bezier_length[-1])
# The only varying noncircular length on slot 3 is its cubic, since its
# translated quarter-circle has a fixed radius and turning angle.
assert fan_speed<1.25 and fan_length_speed<2.5
amp=1.8875;upper_core_speed=math.sqrt((.2+amp)**2+.3**2+Hprime**2)
contact_speed=math.sqrt((.2+amp)**2+.3**2+(Hprime+fan_length_speed+amp)**2)
assert upper_core_speed<2.25 and contact_speed<6.
upper_radius=1./(amp*(10*math.sqrt(3)/3)/16.**2)
free_gap=1./math.sqrt(1.+(amp*1.875/16.)**2)-.6604
remaining_lower=finite['minimum_terminal_straight_mm']-(fan_length_speed+amp)/80.
assert upper_radius>7. and free_gap>.3 and remaining_lower>2.
# The fourth S-bend's extra rise cancels H(d). Remaining straight is
# smallest at the largest third-bend X reach (f=0).
def fan_line(f):
    deltas=[c0['start_mm'][0]-par['side_x_mm'],par['side_y_mm']-c0['start_mm'][1],dx0+.2*(1-f),dy+1.8-.3*f]
    rise=sum(2*radius*math.sin(math.acos(1-delta/(2*radius))) for delta,radius in zip(deltas,par['radii_mm']))
    return c0['end_mm'][2]+height(1.8-.3*f)-c0['start_mm'][2]-rise
line_lower=fan_line(0.)-1e-9;assert line_lower>0. and fan_line(1.)>=line_lower
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Entire recovery fraction 0..1: curve curvature, span displacement, tail length and parallel packing; collision checks separate',
    script_sha256=sha(SCRIPT),source_finite_sha256=sha(finite_path),source_fan_pool_sha256=sha(pool_path),
    source_main_sha256=finite['source_main_sha256'],bezier_spans=rows,circular_radius_mm=7.2,
    upper_radius_lower_mm=upper_radius,fan_straight_length_lower_mm=line_lower,
    root_height_derivative_bound=Hprime,fan_displacement_derivative_bound=fan_speed,
    fan_length_derivative_bound=fan_length_speed,upper_core_displacement_derivative_bound=upper_core_speed,
    contact_displacement_derivative_bound=contact_speed,
    chosen_fan_lipschitz=1.25,chosen_upper_core_lipschitz=2.25,chosen_contact_lipschitz=6.,
    minimum_terminal_straight_whole_family_mm=remaining_lower,
    free_free_gap_lower_bound_mm=free_gap,
    contact_contact_basis='All four contact X centres stay exactly 1 mm apart; the stated boxes have 1 mm X width and common fixed orientation. Touching only, without manufacturing clearance.',
    span_mapping='Fixed normalized parameter per circle, Bezier, straight or free-terminal span; not a material-strain simulation',
    physical_wire_torsion_and_bend_life='NOT_TESTED',continuous_collision='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'math_bounds.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('ORDERED_RECOVERY_MATH_DONE',report['status'],fan_speed,fan_length_speed,contact_speed,round(time.time()-started,1),flush=True)
