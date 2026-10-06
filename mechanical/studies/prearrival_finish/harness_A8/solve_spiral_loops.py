"""Finite smooth spiral family, A8 four independent UART wire candidates.

The radial profile varies throughout the loop rather than using a circular
middle plateau. Endpoints and tangent directions stay fixed in their respective
body/yaw frames. No anchors, retention hardware or main geometry are changed.
"""
from pathlib import Path
import math,json,hashlib,time,itertools,collections
import numpy as np
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent
space_path=HERE/'uart_space.json';space=json.loads(space_path.read_text())
od=space['wire_od_max_mm'];radius=od/2;gap=.3
requirement=space['wire_catalogue_bend_reference_mm']+radius
started=time.time();outrows=[];tested=0;rejects=collections.Counter()
# Quintic monotone base and quartic zero-end-slope displacement.
S=np.array([0,0,0,10,-15,6.])
B=np.array([0,0,16,-32,16,0.])
t=np.linspace(0,1,1201)
qn,qw=np.polynomial.legendre.leggauss(96);qt=(qn+1)/2;qw=qw/2

def coeff(a,b,c):
    co=(b-a)*S+c*B;co[0]+=a;return co
def extrema(co):
    roots=poly.polyroots(poly.polyder(co))
    ts=[0.,1.]+[float(x.real) for x in roots if abs(x.imag)<1e-8 and 0<x.real<1]
    v=poly.polyval(ts,co);return float(v.min()),float(v.max())
def profile_bounds(a,b,lo,hi):
    bounds=[]
    for sign in [-1,1]:
        low,high=0.,40.
        for _ in range(42):
            m=(low+high)/2;mi,ma=extrema(coeff(a,b,sign*m))
            if mi>=lo+1e-5 and ma<=hi-1e-5:low=m
            else:high=m
        bounds.append(sign*low)
    return bounds
def length(c,a,b,alpha):
    co=coeff(a,b,c);r=poly.polyval(qt,co);dr=poly.polyval(qt,poly.polyder(co))
    return float(np.sum(qw*np.sqrt(dr*dr+alpha*alpha*r*r)))
def slope(c,a,b,alpha):
    co=coeff(a,b,c);r=poly.polyval(qt,co);dr=poly.polyval(qt,poly.polyder(co))
    db=poly.polyval(qt,B);ddb=poly.polyval(qt,poly.polyder(B))
    return float(np.sum(qw*(dr*ddb+alpha*alpha*r*db)/np.sqrt(dr*dr+alpha*alpha*r*r)))
def solve(L,a,b,alpha,cmin,cmax):
    for _ in range(42):
        mid=(cmin+cmax)/2
        if length(mid,a,b,alpha)<L:cmin=mid
        else:cmax=mid
    return (cmin+cmax)/2

levels=sorted(space['levels'],key=lambda x:-(max(x['accepted_static_circle_radii_mm'])-min(x['accepted_static_circle_radii_mm'])))
for level in levels[:3]:
    lo=min(level['accepted_static_circle_radii_mm']);hi=max(level['accepted_static_circle_radii_mm'])
    selected=[];best=None
    for inset_a,inset_b,nominal,fraction in itertools.product([.75,1.5,2.5],[.75,1.5,2.5],range(600,1201,30),[.1,.3,.5,.7,.9]):
        tested+=1;a=lo+inset_a;b=hi-inset_b;cmin,cmax=profile_bounds(a,b,lo,hi)
        alphas=[math.radians(nominal+y) for y in [-60,0,60]]
        if min(slope(cmin,a,b,q) for q in alphas)<=0:rejects['length_not_monotone']+=1;continue
        low=max(length(cmin,a,b,q) for q in alphas);high=min(length(cmax,a,b,q) for q in alphas)
        if low>high:rejects['no_common_length']+=1;continue
        L=low+fraction*(high-low);poses=[];bad=None
        for yaw in range(-60,61,10):
            alpha=math.radians(nominal+yaw);c=solve(L,a,b,alpha,cmin,cmax);co=coeff(a,b,c)
            r=poly.polyval(t,co);dr=poly.polyval(t,poly.polyder(co));dd=poly.polyval(t,poly.polyder(co,2))
            curvature=np.abs(alpha*(2*dr*dr+r*(alpha*alpha*r-dd)))/(dr*dr+alpha*alpha*r*r)**1.5
            minR=1/max(float(curvature.max()),1e-20)
            if minR<requirement:bad='sampled_bend_radius';break
            theta=-math.radians(nominal)+alpha*t
            pts=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.full(len(t),level['midplane_z_mm'])])
            chords=np.linalg.norm(np.diff(pts,axis=0),axis=1);arcs=np.r_[0,np.cumsum(chords)]
            dmin,dmax=extrema(poly.polyder(co));ddmin,ddmax=extrema(poly.polyder(co,2))
            second=max(abs(ddmin),abs(ddmax))+2*alpha*max(abs(dmin),abs(dmax))+alpha*alpha*hi
            error=second/(len(t)-1)**2/8
            # For pairs separated by a substantial parameter interval, use
            # vertex-to-segment distances and cover between-vertex points.
            coarse=pts[::4];s=arcs[::4];mask=np.abs(s[:,None]-s[None,:])>math.pi*(radius+gap)
            nearest=float(np.linalg.norm(coarse[:,None,:]-coarse[None,:,:],axis=2)[mask].min())
            if nearest<2*(radius+gap):bad='sampled_nonlocal_overlap';break
            lower=nearest-8*chords.max()-2*error
            if lower<2*(radius+gap):
                # Chunk the full segment comparison to keep peak memory low.
                vv=np.diff(pts,axis=0);lower=1e9
                for i in range(0,len(pts),128):
                    ww=pts[i:i+128,None,:]-pts[:-1][None,:,:]
                    uu=np.clip(np.sum(ww*vv[None,:,:],axis=2)/np.sum(vv*vv,axis=1)[None,:],0,1)
                    ds=np.linalg.norm(ww-uu[:,:,None]*vv[None,:,:],axis=2)
                    far=(np.abs(arcs[i:i+128,None]-arcs[:-1][None,:])>math.pi*(radius+gap))&(np.abs(arcs[i:i+128,None]-arcs[1:][None,:])>math.pi*(radius+gap))
                    if far.any():lower=min(lower,float(ds[far].min()))
                lower-=chords.max()/2+2*error
                if lower<2*(radius+gap):bad='nonlocal_clearance_unresolved';break
            poses.append(dict(yaw_deg=yaw,radial_displacement_mm=c,centreline_length_mm=length(c,a,b,alpha),
                radial_polynomial_coefficients=co.tolist(),midplane_curve_mm=pts.tolist(),
                sampled_minimum_curvature_radius_mm=minR,nonlocal_distance_lower_bound_mm=lower,
                second_derivative_chord_error_bound_mm=error))
        case=dict(nominal_angle_deg=nominal,start_radius_mm=a,end_radius_mm=b,
            radial_displacement_bounds_mm=[cmin,cmax],length_interval_fraction=fraction,
            each_yaw_segment_length_mm=L,completed_pose_count=len(poses),failure=bad)
        if best is None or len(poses)>best['completed_pose_count']:best=case
        if bad:rejects[bad]+=1;continue
        selected=[dict(**case,poses=poses)]
        print('A8_SPIRAL_SURVIVOR',level['midplane_z_mm'],nominal,a,b,L,round(time.time()-started,2),flush=True)
        break
    outrows.append(dict(midplane_z_mm=level['midplane_z_mm'],individual_plane_z_mm=level['individual_plane_z_mm'],
        static_radius_interval_mm=[lo,hi],status='PASS' if selected else 'BLOCKED',selected=selected,best_partial=best))
    print('A8_SPIRAL_LEVEL',level['midplane_z_mm'],outrows[-1]['status'],tested,dict(rejects),round(time.time()-started,2),flush=True)
    if selected:break
out=dict(status='PASS' if any(r['selected'] for r in outrows) else 'BLOCKED',
    scope='Finite smooth radial-profile four-wire UART yaw planning paths only',
    source_blend_sha256=space['source_blend_sha256'],source_space_sha256=hashlib.sha256(space_path.read_bytes()).hexdigest(),
    wire_od_max_mm=od,wire_catalogue_bend_reference_mm=space['wire_catalogue_bend_reference_mm'],
    applied_centreline_radius_requirement_mm=requirement,wire_count=4,total_head_yaw_conductors=11,
    classification='PLACEHOLDER / ASSUMED independent route allocations',
    interwire_z_spacing_mm=od+space['within_group_surface_gap_assumed_mm'],
    levels=outrows,candidates_tested=tested,rejections=dict(rejects),elapsed_s=time.time()-started,
    main_geometry_changed=False,limits=['Candidate midplane curve is copied to four Z planes; each geometric length is therefore individually preserved.',
        'Finite pose and numerical curvature sampling; no continuous-motion or lifetime certification.',
        'No sleeve, twist, tape, wire order restraint or real anchors modeled.',
        'The path still needs source-solid, adjacent loops and fixed-wire validation.',
        'Staging endpoints and segment lengths are not connector positions or cutting lengths.'])
(HERE/'uart_spiral_loops.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
