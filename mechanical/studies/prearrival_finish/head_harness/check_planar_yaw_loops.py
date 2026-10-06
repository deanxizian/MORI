"""Constant-centreline-length polar loops inside the measured planning annulus.

This tests an explicit finite family for the whole 11-wire allocation. No
endpoints are called physical anchors and no bundle is selected or adopted.
"""
from pathlib import Path
import json,hashlib,math,itertools,time,collections
import numpy as np
HERE=Path(__file__).resolve().parent
src=HERE/'yaw_loop_space.json';space=json.loads(src.read_text())
level=next(x for x in space['results'] if x['z_mm']==152.5)
allowed=[x['centre_radius_mm'] for x in level['accepted_circles']]
lo,hi=min(allowed),max(allowed)
radius=space['conservative_enclosing_diameter_mm']/2;gap=space['project_external_gap_mm']
minimum_bend=14.224+radius
start=time.time();reject=collections.Counter();count=0;passing=[];length_examples=[]

def smooth(q):return 10*q**3-15*q**4+6*q**5
def smooth_d(q):return 30*q*q-60*q**3+30*q**4
def smooth_dd(q):return 60*q-180*q*q+120*q**3
def basis(t,u,v,a,b):
    # r=A+B*middle, dr=C+D*middle, ddr=E+F*middle.
    A=np.zeros_like(t);B=np.ones_like(t);C=np.zeros_like(t);D=np.zeros_like(t);E=np.zeros_like(t);F=np.zeros_like(t)
    mask=t<u;q=t[mask]/u;S=smooth(q);Sd=smooth_d(q)/u;Sdd=smooth_dd(q)/(u*u)
    A[mask]=a*(1-S);B[mask]=S;C[mask]=-a*Sd;D[mask]=Sd;E[mask]=-a*Sdd;F[mask]=Sdd
    mask=t>1-v;q=(t[mask]-1+v)/v;S=smooth(q);Sd=smooth_d(q)/v;Sdd=smooth_dd(q)/(v*v)
    A[mask]=b*S;B[mask]=1-S;C[mask]=b*Sd;D[mask]=-Sd;E[mask]=b*Sdd;F[mask]=-Sdd
    return A,B,C,D,E,F

nodes,weights=np.polynomial.legendre.leggauss(24)
def quadrature(u,v,a,b):
    ts=[];ws=[]
    for x,y in [(0,u),(u,1-v),(1-v,1)]:
        ts.extend((x+(nodes+1)*(y-x)/2).tolist());ws.extend((weights*(y-x)/2).tolist())
    return np.asarray(ws),basis(np.asarray(ts),u,v,a,b)
def length(mid,alpha,q):
    w,(A,B,C,D,_,_)=q;r=A+B*mid;dr=C+D*mid
    return float(np.sum(w*np.sqrt(dr*dr+alpha*alpha*r*r)))
def solve(L,alpha,q):
    l,h=lo,hi
    for _ in range(42):
        m=(l+h)/2
        if length(m,alpha,q)<L:l=m
        else:h=m
    return (l+h)/2

for nominal,a,b,u,v in itertools.product(range(240,541,15),[37.,40.,44.,48.,52.],[37.,40.,44.,48.,52.],[.15,.25,.35,.45,.55],[.15,.25,.35]):
    if u+v>=.95:continue
    count+=1;q=quadrature(u,v,a,b)
    alphas=[math.radians(nominal+yaw) for yaw in [-60,0,60]]
    intervals=[(length(lo,alpha,q),length(hi,alpha,q)) for alpha in alphas]
    low=max(x[0] for x in intervals);high=min(x[1] for x in intervals)
    if high<low:
        reject['no_constant_length_interval']+=1
        if len(length_examples)<5:length_examples.append(dict(nominal_angle_deg=nominal,start_radius_mm=a,end_radius_mm=b,entry_fraction=u,exit_fraction=v,common_interval_mm=[low,high]))
        continue
    L=(low+high)/2;poses=[];bad=None
    t=np.linspace(0,1,801);A,B,C,D,E,F=basis(t,u,v,a,b)
    for yaw in range(-60,61,10):
        alpha=math.radians(nominal+yaw);middle=solve(L,alpha,q)
        r=A+B*middle;dr=C+D*middle;dd=E+F*middle
        speed2=dr*dr+alpha*alpha*r*r
        curvature=np.abs(alpha*(2*dr*dr+r*(alpha*alpha*r-dd)))/np.maximum(speed2,1e-10)**1.5
        minR=1/max(float(curvature.max()),1e-20)
        if minR<minimum_bend:bad='sampled_bend_radius';break
        # End lies on rotating +X datum at zero; body end stays at -nominal.
        theta=math.radians(-nominal)+alpha*t
        pts=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.full(len(t),152.5)])
        chords=np.linalg.norm(np.diff(pts,axis=0),axis=1);s=np.r_[0,np.cumsum(chords)]
        # Only nonlocal distances; local tube regularity is also screened by
        # a centreline curvature radius larger than the complete envelope.
        coarse=pts[::4];ss=s[::4];dist=np.linalg.norm(coarse[:,None,:]-coarse[None,:,:],axis=2)
        mask=np.abs(ss[:,None]-ss[None,:])>math.pi*(radius+gap)
        nonlocal_lower=float(dist[mask].min()-2*max(chords)*4)
        if nonlocal_lower<2*(radius+gap):bad='nonlocal_self_clearance';break
        poses.append(dict(yaw_deg=yaw,middle_radius_mm=middle,centerline_length_mm=length(middle,alpha,q),
            sampled_minimum_curvature_radius_mm=minR,nonlocal_distance_lower_bound_mm=nonlocal_lower,curve_mm=pts.tolist()))
    if bad:reject[bad]+=1;continue
    passing.append(dict(nominal_angle_deg=nominal,start_radius_mm=a,end_radius_mm=b,entry_fraction=u,exit_fraction=v,
        centerline_length_mm=L,poses=poses))
    print('PLANAR_LOOP_SURVIVOR',nominal,a,b,u,v,L,flush=True)
    # The family is a feasibility screen, not a shortest-route optimization.
    # One survivor is enough to justify detailed source-solid validation.
    break

out=dict(status='PASS' if passing else 'BLOCKED',scope='Finite planar polar-loop kinematic planning family only',
    source_space_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),source_blend_sha256=space['source_blend_sha256'],
    whole_eleven_wire_allocation=True,conservative_bundle_diameter_mm=2*radius,
    plane_z_mm=152.5,screened_center_radius_interval_mm=[lo,hi],static_wire_bend_basis_mm=14.224,
    required_centerline_bend_radius_mm=minimum_bend,project_gap_mm=gap,candidates_tested=count,
    rejections=dict(reject),constant_length_failure_examples=length_examples,selected=passing,elapsed_s=time.time()-start,
    actual_anchor_interfaces='NOT_TESTED',individual_wire_lengths='NOT_TESTED',actual_solid_motion='NOT_TESTED',
    main_geometry_changed=False,limits=['Packing and cable construction are allocations, not selected or measured bundles.',
        'Constant centreline length does not establish constant length of each packed wire or acceptable inter-wire sliding.',
        'Circular-source sampling does not certify all intermediate radii of a new spiral; any survivor needs exact source-solid checks.',
        'Bend screening is dense nominal sampling, not a certified global curvature bound or dynamic life.',
        'A failed finite family does not rule out split, nonplanar or other routed loops.'])
(HERE/'planar_yaw_loops.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PLANAR_YAW_LOOPS',out['status'],count,dict(reject),time.time()-start,flush=True)
