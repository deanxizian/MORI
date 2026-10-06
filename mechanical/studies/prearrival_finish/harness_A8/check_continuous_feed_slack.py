"""Bound the whole angular-slack interpolation, not just 11 sampled shapes.

Only the central segment changes during this step. End positions/tangents are
held, loose tail supplies length, and yaw/pitch stay at zero for assembly.
"""
from pathlib import Path
SLACK_SCRIPT=Path(__file__).resolve();SLACK_DIR=SLACK_SCRIPT.parent
SLACK_HELPER=SLACK_DIR/'plan_h06_documented_mates.py';__file__=str(SLACK_HELPER)
exec(compile(SLACK_HELPER.read_text().split('\nports=json.loads',1)[0],str(SLACK_HELPER),'exec'),globals())
__file__=str(SLACK_SCRIPT);OUT=SLACK_DIR/'assembly_feed_v3/open_mouth';SLACK_START=time.time()
from numpy.polynomial import polynomial as poly
from mathutils.kdtree import KDTree
from interface_completion import replace_owned
for name in ['Yaw_Base','Pitch_Yoke']:
    raw=np.load(OUT/'cleaned'/f'{name}.npz');m=manifold.Manifold(manifold.Mesh64(vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
    obj=ss[name].o;replace_owned(name,m);ss[name]=Solid(obj);obstacles[name]=ss[name];trees[name]=ss[name].bvh()
data=json.loads((SLACK_DIR/'central_uart_curves.json').read_text())
zero=next(r for r in data['selected']['poses'] if r['yaw_deg']==0)
co=np.array(zero['angular_polynomial_coefficients']);dc=poly.polyder(co);ddc=poly.polyder(dc)
r0=6.8;h=32.;n=2049;t=np.linspace(0,1,n);theta=poly.polyval(t,co)
def range_of(coeff,lo,hi):
    roots=poly.polyroots(poly.polyder(coeff));args=[lo,hi]+[float(x.real) for x in roots if abs(x.imag)<1e-8 and lo<x.real<hi]
    values=poly.polyval(args,coeff);return float(values.min()-1e-8),float(values.max()+1e-8)
dlo,dhi=range_of(dc,0,1);ddlo,ddhi=range_of(ddc,0,1);dmax=max(abs(dlo),abs(dhi));ddmax=max(abs(ddlo),abs(ddhi))

# Numerical interval bounds for curvature across the (t,u) rectangle.
k_bounds=[]
for ta,tb in zip(np.linspace(0,1,257)[:-1],np.linspace(0,1,257)[1:]):
    lo,hi=range_of(dc,float(ta),float(tb));D=max(abs(lo),abs(hi));Dmin=0. if lo<=0<=hi else min(abs(lo),abs(hi))
    lo,hi=range_of(ddc,float(ta),float(tb));DD=max(abs(lo),abs(hi))
    for ua,ub in zip(np.linspace(0,1,65)[:-1],np.linspace(0,1,65)[1:]):
        numerator=r0*math.sqrt(h*h*(ub**4*D**4+ub**2*DD**2)+r0*r0*ub**6*D**6)
        denominator=(h*h+r0*r0*ua*ua*Dmin*Dmin-1e-8)**1.5
        k_bounds.append(numerator/denominator+1e-12)
bend_bound=1/max(k_bounds);assert bend_bound>=REQUIRED_R,(bend_bound,REQUIRED_R)

pack=json.loads((SLACK_DIR/'body_prefix_v2/packing.json').read_text())
meta=json.loads((SLACK_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
curves=np.load(SLACK_DIR/'body_prefix_v2/body_to_yaw_curves.npz');other={}
for row in pack['selected']:
    points=curves[f'pin{row["pin"]}_yaw0'];fine=[]
    for a,b in zip(points,points[1:]):fine.extend(np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.02))+1)[:-1])
    fine=np.vstack([fine,points[-1:]]);kd=KDTree(len(fine))
    for ix,p in enumerate(fine):kd.insert(Vector(p),ix)
    kd.balance();err=next(q['curve_error_bound_mm'] for q in meta['rows'] if q['pin']==row['pin'] and q['yaw_deg']==0)
    other[row['azimuth_deg']]=(kd,err)

allobs=[(name,s.lo,s.hi,s.m,trees[name]) for name,s in obstacles.items()]
allobs += [(name,s['lo'],s['hi'],s['m'],s['tree']) for name,s in fixed.items()]
def check_interval(ua,ub,phase):
    um=(ua+ub)/2;ang=theta*um+math.radians(phase)
    points=np.column_stack([r0*np.cos(ang),r0*np.sin(ang),147+h*t])
    step=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max())
    error=r0*(ub*ub*dmax*dmax+ub*ddmax)/(n-1)**2/8
    movement=r0*(np.abs(theta)+dmax/(n-1)/2)*(ub-ua)/2
    allowance=OD/2+MARGIN+step/2+error+movement+1e-4
    minimum=math.inf
    for name,lo,hi,solid,tree in allobs:
        mask=np.all(points>=lo-allowance[:,None],axis=1)&np.all(points<=hi+allowance[:,None],axis=1)
        indexes=np.flatnonzero(mask)
        for i in indexes:
            distance=float(tree.find_nearest(Vector(points[i]))[3]);slack=distance-allowance[i];minimum=min(minimum,slack)
            if slack<0:return {'status':'REFINE','object':name,'sample':int(i),'bound_slack_mm':float(slack)}
        starts=indexes[np.r_[True,np.diff(indexes)>1]] if len(indexes) else []
        for i in starts:
            if np.all(points[i]>=lo) and np.all(points[i]<=hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(points[i].tolist())
                if (tiny^solid).volume()>tiny.volume()/2:return {'status':'BLOCKED','object':name,'inside':True}
    pair_min=math.inf
    for phase2,(kd,err2) in other.items():
        if phase2==phase:continue
        # Per-sample movement bound covers all intermediate u; .01 covers
        # nearest sampling on the other line, plus both curve errors and OD.
        for i,p in enumerate(points):
            distance=float(kd.find(Vector(p))[2])
            gap=distance-step/2-.01-error-err2-OD-movement[i]-1e-4
            pair_min=min(pair_min,gap)
            if gap<MARGIN:return {'status':'REFINE','object':'UART_phase_'+str(phase2),'bound_slack_mm':float(gap-MARGIN)}
    return {'status':'PASS','minimum_source_extra_margin_bound_mm':float(minimum),'other_wire_surface_gap_bound_mm':float(pair_min),
        'curve_error_bound_mm':float(error),'maximum_motion_from_midshape_bound_mm':float(movement.max())}

accepted=[];attempts=[];failed=[]
for phase in [45,135,225,315]:
    pending=[(0.,1.,0)]
    while pending:
        ua,ub,depth=pending.pop();result=check_interval(ua,ub,phase)
        row={'phase_deg':phase,'u_interval':[ua,ub],'depth':depth,**result};attempts.append(row)
        if result['status']=='PASS':accepted.append(row)
        elif result['status']=='REFINE' and depth<10:
            mid=(ua+ub)/2;pending.extend([(mid,ub,depth+1),(ua,mid,depth+1)])
        else:failed.append(row)
    print('CONTINUOUS_SLACK_PHASE',phase,len(accepted),len(failed),round(time.time()-SLACK_START,2),flush=True)
for phase in [45,135,225,315]:
    span=sum(r['u_interval'][1]-r['u_interval'][0] for r in accepted if r['phase_deg']==phase)
    if not any(r['phase_deg']==phase for r in failed):assert abs(span-1)<1e-12
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'PASS' if not failed else 'BLOCKED',
    'scope':'Continuous prescribed central angular-slack interpolation u0..1 at yaw/pitch zero; loose-tail manual operation remains untested',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(SLACK_SCRIPT),'source_helper_sha256':sha(SLACK_HELPER),
    'source_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),
    'source_central_law_sha256':sha(SLACK_DIR/'central_uart_curves.json'),'source_installed_curves_sha256':sha(SLACK_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'method':'Adaptive u intervals, pointwise analytic radial-motion bound, curve-to-chord and spatial sample bounds, closed-solid containment check',
    'bending_method':'Numerical polynomial extrema in256t cells and64u cells, with outward1e-8 range allowance',
    'central_bend_radius_lower_bound_mm':bend_bound,'required_bend_radius_mm':REQUIRED_R,
    'accepted_intervals':accepted,'refinement_attempts':attempts,'unresolved_intervals':failed,
    'unchanged_lower_and_upper_curves':'Covered by prior stage endpoints and source replay',
    'free_tail_feeding':'NOT_TESTED','hands_and_tool_access':'NOT_TESTED','friction_and_dynamic_life':'NOT_TESTED',
    'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-SLACK_START}
(OUT/'continuous_slack.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONTINUOUS_SLACK_DONE',result['status'],bend_bound,len(accepted),flush=True)
