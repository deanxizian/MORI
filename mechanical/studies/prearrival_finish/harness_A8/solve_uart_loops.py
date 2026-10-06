"""A8 catalogue-wire candidate: four independent equal-length planar loops.

Planning endpoints are not anchors. No main geometry, pin map or wire purchase
selection changes. A later test must evaluate the current source solids.
"""
from pathlib import Path
import json, hashlib, math, itertools, collections, time
import numpy as np

HERE=Path(__file__).resolve().parent
source=HERE/'uart_space.json'; space=json.loads(source.read_text())
helper=HERE.parent/'head_harness/check_planar_yaw_loops.py'
code=helper.read_text()
exec(compile(code[code.index('def smooth'):code.index('for nominal,')],str(helper),'exec'),globals())
started=time.time();od=space['wire_od_max_mm'];radius=od/2;gap=.3
required=space['wire_catalogue_bend_reference_mm']+radius
results=[];tried=0
levels=sorted(space['levels'],key=lambda r:(-(max(r['accepted_static_circle_radii_mm'],default=0)-min(r['accepted_static_circle_radii_mm'],default=0)),r['midplane_z_mm']))
for level in levels:
    radii=level['accepted_static_circle_radii_mm']
    if len(radii)<2: continue
    runs=[]
    for _,rows in itertools.groupby(enumerate(radii),lambda x:round(x[1]-.5*x[0],6)):
        run=[r[1] for r in rows];runs.append(run)
    accepted=max(runs,key=len);lo,hi=accepted[0],accepted[-1]
    if lo==hi:continue
    rejects=collections.Counter();chosen=[];best=None
    # Begin near the historical seven-pose survivor instead of repeating a
    # broad low-angle family before testing the new smaller wire candidate.
    priority=[(440,lo,hi,.15,.15,.05),(450,lo,hi,.15,.15,.05),
              (460,lo,hi,.15,.15,.05),(480,lo,hi,.25,.15,.05)]
    family=itertools.product(range(330,701,10),np.linspace(lo,hi,3),np.linspace(lo,hi,3),[.15,.25,.35,.45,.55],[.15,.25,.35],[.05,.5,.95])
    for nominal,a,b,u,v,fraction in itertools.chain(priority,family):
        if u+v>=.95:continue
        tried+=1;q=quadrature(u,v,a,b)
        if tried%1000==0:print('A8_SEARCH',tried,level['midplane_z_mm'],nominal,round(time.time()-started,2),flush=True)
        alphas=[math.radians(nominal+y) for y in [-60,0,60]]
        w,(Q0,Q1,Q2,Q3,_,_)=q
        derivatives=[float(np.sum(w*((Q2+Q3*lo)*Q3+aa*aa*(Q0+Q1*lo)*Q1)/np.sqrt((Q2+Q3*lo)**2+aa*aa*(Q0+Q1*lo)**2))) for aa in alphas]
        if min(derivatives)<=0:rejects['unresolved_length_monotonicity']+=1;continue
        intervals=[(length(lo,aa,q),length(hi,aa,q)) for aa in alphas]
        low=max(x[0] for x in intervals);high=min(x[1] for x in intervals)
        if low>high:rejects['no_common_length']+=1;continue
        L=low+(high-low)*fraction;t=np.linspace(0,1,1001)
        A,B,C,D,E,F=basis(t,u,v,a,b);poses=[];bad=None
        for yaw in range(-60,61,10):
            alpha=math.radians(nominal+yaw);middle=solve(L,alpha,q)
            r=A+B*middle;dr=C+D*middle;dd=E+F*middle
            speed2=dr*dr+alpha*alpha*r*r
            curvature=np.abs(alpha*(2*dr*dr+r*(alpha*alpha*r-dd)))/np.maximum(speed2,1e-10)**1.5
            minR=1/max(float(curvature.max()),1e-20)
            if minR<required:bad='sampled_bend_radius';break
            theta=math.radians(-nominal)+alpha*t
            pts=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.full(len(t),level['midplane_z_mm'])])
            chord=np.linalg.norm(np.diff(pts,axis=0),axis=1);arcs=np.r_[0,np.cumsum(chord)]
            second_bound=6*(hi-lo)/min(u,v)**2+2*alpha*1.875*(hi-lo)/min(u,v)+alpha*alpha*hi
            error=second_bound/((len(t)-1)**2*8)
            coarse=pts[::4];s=arcs[::4]
            mask=np.abs(s[:,None]-s[None,:])>math.pi*(radius+gap)
            distances=np.linalg.norm(coarse[:,None,:]-coarse[None,:,:],axis=2)
            nominal_min=float(distances[mask].min())
            if nominal_min<2*(radius+gap):bad='sampled_nonlocal_overlap';break
            lower=nominal_min-2*chord.max()*4-2*error
            if lower<2*(radius+gap):
                vv=np.diff(pts,axis=0);ww=pts[:,None,:]-pts[:-1][None,:,:]
                tt=np.clip(np.sum(ww*vv[None,:,:],axis=2)/np.sum(vv*vv,axis=1)[None,:],0,1)
                ds=np.linalg.norm(ww-tt[:,:,None]*vv[None,:,:],axis=2)
                far=(np.abs(arcs[:,None]-arcs[:-1][None,:])>math.pi*(radius+gap))&(np.abs(arcs[:,None]-arcs[1:][None,:])>math.pi*(radius+gap))
                # Each point of first polyline is within half its longest
                # chord of a sampled vertex. Include that coverage margin.
                lower=float(ds[far].min())-chord.max()/2-2*error
                if lower<2*(radius+gap):bad='nonlocal_clearance_unresolved';break
            poses.append(dict(yaw_deg=yaw,middle_radius_mm=middle,centreline_length_mm=length(middle,alpha,q),
                sampled_minimum_curvature_radius_mm=minR,nonlocal_distance_lower_bound_mm=lower,
                second_derivative_chord_error_bound_mm=error,midplane_curve_mm=pts.tolist()))
        case=dict(nominal_angle_deg=nominal,start_radius_mm=float(a),end_radius_mm=float(b),entry_fraction=u,
            exit_fraction=v,length_interval_fraction=fraction,each_yaw_segment_length_mm=L,
            completed_pose_count=len(poses),failure=bad)
        if best is None or len(poses)>best['completed_pose_count']:best=case
        if bad:rejects[bad]+=1;continue
        chosen.append(dict(**case,poses=poses))
        print('A8_PLANAR_SURVIVOR',level['midplane_z_mm'],nominal,a,b,L,round(time.time()-started,2),flush=True)
        break
    results.append(dict(midplane_z_mm=level['midplane_z_mm'],individual_plane_z_mm=level['individual_plane_z_mm'],
        static_radius_interval_mm=[lo,hi],status='PASS' if chosen else 'BLOCKED',
        rejections=dict(rejects),best_partial=best,selected=chosen))
    print('A8_PLANAR_LEVEL',level['midplane_z_mm'],results[-1]['status'],dict(rejects),round(time.time()-started,2),flush=True)
    if len([r for r in results if r['selected']])>=3:break
out=dict(status='PASS' if any(r['selected'] for r in results) else 'BLOCKED',
    scope='Finite same-length four-wire UART yaw planning paths only',
    source_blend_sha256=space['source_blend_sha256'],source_space_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    source_math_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),wire_od_max_mm=od,
    wire_catalogue_bend_reference_mm=space['wire_catalogue_bend_reference_mm'],
    applied_centreline_radius_requirement_mm=required,wire_count=4,total_head_yaw_conductors=11,
    classification='PLACEHOLDER / ASSUMED independent route allocations',
    interwire_z_spacing_mm=od+space['within_group_surface_gap_assumed_mm'],
    candidates_tested=tried,levels=results,elapsed_s=time.time()-started,main_geometry_changed=False,
    limitations=['Four curves differ by a constant Z translation, so their geometric lengths match individually.',
        'Curvature is sampled numerically at 13 yaw poses, not a continuous-motion or dynamic-life guarantee.',
        'No sleeve, twist, tape or clamps modeled. Required separation within four free wires is not guaranteed physically.',
        'Source-solid, other-loop and fixed-wire clearances need separate verification.',
        'Endpoints are staging points; segment length is not a cut length or manufacturing length.'])
(HERE/'uart_loops.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A8_PLANAR_COMPLETE',out['status'],tried,round(time.time()-started,2),flush=True)
