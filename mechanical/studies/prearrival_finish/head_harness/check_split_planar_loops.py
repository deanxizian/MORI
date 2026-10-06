"""Three constant-length planning centrelines for all11 functional conductors.

Each group has fixed body-frame and yaw-frame staging coordinates. Real clamps,
individual wire sliding, actual terminal cables and head approaches are pending.
"""
from pathlib import Path
import json,hashlib,math,itertools,time,collections,sys
import numpy as np
HERE=Path(__file__).resolve().parent
source=HERE/'split_yaw_space.json';space=json.loads(source.read_text())
helper=HERE/'check_planar_yaw_loops.py';code=helper.read_text()
exec(compile(code[code.index('def smooth'):code.index('for nominal,')],str(helper),'exec'),globals())
all_results=[];started=time.time()
REFINE='--refine' in sys.argv
previous=json.loads((HERE/'split_planar_loops.json').read_text()) if REFINE else None

for group in space['groups']:
    if REFINE:
        earlier=next(g for g in previous['groups'] if g['id']==group['id'])
        if earlier['status']=='PASS':all_results.append(earlier);continue
    lo,hi=min(group['accepted_centre_radii_mm']),max(group['accepted_centre_radii_mm'])
    radius=group['enclosing_diameter_mm']/2;gap=.3;required=group['bend']+radius
    rejects=collections.Counter();count=0;passing=None;best=None
    ends=np.linspace(lo,hi,3) if REFINE else np.linspace(lo+.5,hi-.5,5)
    fractions=[.05,.25,.5,.75,.95] if REFINE else [.5]
    for nominal,a,b,u,v,fraction in itertools.product(range(270,541,10) if REFINE else range(240,601,15),ends,ends,[.15,.25,.35,.45,.55],[.15,.25,.35],fractions):
        if u+v>=.95:continue
        count+=1;q=quadrature(u,v,a,b)
        if count%2500==0:print('SPLIT_LOOP_SEARCH',group['id'],count,time.time()-started,flush=True)
        alphas=[math.radians(nominal+y) for y in [-60,0,60]]
        # Integral of norms of affine functions is convex in middle radius.
        # Positive derivative at lo proves monotonicity over [lo,hi].
        w,(Q0,Q1,Q2,Q3,_,_)=q
        derivatives=[float(np.sum(w*((Q2+Q3*lo)*Q3+aa*aa*(Q0+Q1*lo)*Q1)/np.sqrt((Q2+Q3*lo)**2+aa*aa*(Q0+Q1*lo)**2))) for aa in alphas]
        if min(derivatives)<=0:rejects['unresolved_nonmonotone_length']+=1;continue
        intervals=[(length(lo,aa,q),length(hi,aa,q)) for aa in alphas]
        low=max(x[0] for x in intervals);high=min(x[1] for x in intervals)
        if low>high:rejects['no_constant_length_interval']+=1;continue
        L=low+(high-low)*fraction;t=np.linspace(0,1,801);A,B,C,D,E,F=basis(t,u,v,a,b)
        poses=[];bad=None
        for yaw in range(-60,61,10):
            alpha=math.radians(nominal+yaw);middle=solve(L,alpha,q)
            r=A+B*middle;dr=C+D*middle;dd=E+F*middle
            speed2=dr*dr+alpha*alpha*r*r
            curvature=np.abs(alpha*(2*dr*dr+r*(alpha*alpha*r-dd)))/np.maximum(speed2,1e-10)**1.5
            minR=1/max(float(curvature.max()),1e-20)
            if minR<required:bad='sampled_bend_radius';break
            theta=math.radians(-nominal)+alpha*t
            pts=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.full(len(t),group['z'])])
            chord=np.linalg.norm(np.diff(pts,axis=0),axis=1);arcs=np.r_[0,np.cumsum(chord)]
            second_bound=6*(hi-lo)/min(u,v)**2+2*alpha*1.875*(hi-lo)/min(u,v)+alpha*alpha*hi
            curve_error=second_bound/((len(t)-1)**2*8)
            coarse=pts[::4];s=arcs[::4];mask=np.abs(s[:,None]-s[None,:])>math.pi*(radius+gap)
            distances=np.linalg.norm(coarse[:,None,:]-coarse[None,:,:],axis=2)
            nominal_min=float(distances[mask].min())
            if nominal_min<2*(radius+gap):bad='sampled_nonlocal_envelope_overlap';break
            lower=nominal_min-2*chord.max()*4-2*curve_error
            if lower<2*(radius+gap):
                vv=np.diff(pts,axis=0);ww=pts[:,None,:]-pts[:-1][None,:,:]
                tt=np.clip(np.sum(ww*vv[None,:,:],axis=2)/np.sum(vv*vv,axis=1)[None,:],0,1)
                ddist=np.linalg.norm(ww-tt[:,:,None]*vv[None,:,:],axis=2)
                far=(np.abs(arcs[:,None]-arcs[:-1][None,:])>math.pi*(radius+gap))&(np.abs(arcs[:,None]-arcs[1:][None,:])>math.pi*(radius+gap))
                lower=float(ddist[far].min())-2*curve_error
                if lower<2*(radius+gap):bad='nonlocal_clearance_unresolved_or_overlapping';break
            poses.append(dict(yaw_deg=yaw,middle_radius_mm=middle,centerline_length_mm=length(middle,alpha,q),
                sampled_minimum_curvature_radius_mm=minR,nonlocal_distance_lower_bound_mm=lower,
                second_derivative_chord_error_bound_mm=curve_error,curve_mm=pts.tolist()))
        case=dict(nominal_angle_deg=nominal,start_radius_mm=float(a),end_radius_mm=float(b),entry_fraction=u,exit_fraction=v,length_interval_fraction=fraction,
            centreline_length_mm=L,completed_pose_count=len(poses),failure=bad)
        if best is None or len(poses)>best['completed_pose_count']:best=case
        if bad:rejects[bad]+=1;continue
        passing=dict(**case,poses=poses);break
    all_results.append(dict(id=group['id'],members=group['members'],diameter_mm=2*radius,plane_z_mm=group['z'],
        centre_radius_bounds_mm=[lo,hi],sampled_bend_required_mm=required,status='PASS' if passing else 'BLOCKED',
        candidates_tested=count,rejections=dict(rejects),best_partial_family=best,selected=passing))
    print('SPLIT_LOOP_RESULT',group['id'],all_results[-1]['status'],count,dict(rejects),time.time()-started,flush=True)
out=dict(status='PASS' if all(q['status']=='PASS' for q in all_results) else 'BLOCKED',
    scope='Three planning centreline kinematics; all11 functional wires counted, no installed harness qualification',
    source_blend_sha256=space['source_blend_sha256'],source_space_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    source_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),groups=all_results,elapsed_s=time.time()-started,
    main_geometry_changed=False,actual_anchor_interfaces='NOT_TESTED',individual_wire_lengths='NOT_TESTED',
    detailed_source_solid_motion='NOT_TESTED',limitations=['These are unselected circular planning envelopes, not actual bundled cables.',
        'No real terminal, fixed clamp, tie or head-rise approach is yet attached.',
        'Constant centreline length does not prove that each enclosed wire can move without length change or sliding.',
        'Numerical curvature sampling is not a global mathematical bound or dynamic life test.',
        'Any passing candidate needs current source-solid, inter-group, installation and head-motion validation.'])
(HERE/('split_planar_loops_refined.json' if REFINE else 'split_planar_loops.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
