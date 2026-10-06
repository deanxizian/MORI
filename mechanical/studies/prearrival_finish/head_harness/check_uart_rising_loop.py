"""Finite nonplanar UART service-loop allocations, not selected cables.

The endpoint height difference separates successive turns. No source-solid,
clamp, approach, individual wire length or fatigue qualification is implied.
"""
from pathlib import Path
import sys,json,hashlib,math,itertools,time,collections
import numpy as np
HERE=Path(__file__).resolve().parent
source=HERE/'split_yaw_space.json';space=json.loads(source.read_text());group=next(g for g in space['groups'] if g['id']=='UART')
helper=HERE/'check_planar_yaw_loops.py';code=helper.read_text()
exec(compile(code[code.index('def smooth'):code.index('for nominal,')],str(helper),'exec'),globals())
REFINE='--refine' in sys.argv
lo,hi=35.,48.5 if REFINE else 49.;rad=group['enclosing_diameter_mm']/2;gap=.3;required=group['bend']+rad
rejects=collections.Counter();started=time.time();count=0;seeds=[]

def z_profile(t,z0,z1,rise):
    q=np.clip((t-rise)/(1-rise),0,1);active=t>rise
    z=z0+(z1-z0)*smooth(q)
    dz=(z1-z0)*smooth_d(q)/(1-rise)*active
    ddz=(z1-z0)*smooth_dd(q)/(1-rise)**2*active
    return z,dz,ddz

def quad3(u,v,a,b,z0,z1,rise):
    knots=sorted(set([0,u,1-v,rise,1]));ts=[];ws=[]
    for x,y in zip(knots,knots[1:]):
        ts.extend((x+(nodes+1)*(y-x)/2).tolist());ws.extend((weights*(y-x)/2).tolist())
    ts=np.asarray(ts)
    return np.asarray(ws),basis(ts,u,v,a,b),z_profile(ts,z0,z1,rise)[1]

def length3(m,alpha,q):
    w,(A,B,C,D,_,_),dz=q;r=A+B*m;dr=C+D*m
    return float(np.sum(w*np.sqrt(dr*dr+alpha*alpha*r*r+dz*dz)))

def solve3(L,alpha,q):
    l,h=lo,hi
    for _ in range(42):
        m=(l+h)/2
        if length3(m,alpha,q)<L:l=m
        else:h=m
    return (l+h)/2

# Bounds are deliberately broad planning limits, not certified free space.
# Detailed current-source verification must filter every saved seed.
for nominal,a,b,u,v,z0,z1,rise,fraction in itertools.product(
        [435,465,495,525,555] if REFINE else [345,375,405,435,465],
        [38.,45.,48.] if REFINE else [48.5,45.,38.],[38.,40.],
        [.15,.25,.35],[.35,.45] if REFINE else [.15,.25],
        [158.6,157.8],[164.8,165.8] if REFINE else [165.8,164.8],[.55,.65],[.25,.75]):
    count+=1;q=quad3(u,v,a,b,z0,z1,rise)
    alphas=[math.radians(nominal+y) for y in [-60,0,60]]
    w,(A,B,C,D,_,_),dz=q
    deriv=[float(np.sum(w*((C+D*lo)*D+aa*aa*(A+B*lo)*B)/np.sqrt((C+D*lo)**2+aa*aa*(A+B*lo)**2+dz*dz))) for aa in alphas]
    if min(deriv)<=0:rejects['unresolved_nonmonotone_length']+=1;continue
    low=max(length3(lo,aa,q) for aa in alphas);high=min(length3(hi,aa,q) for aa in alphas)
    if low>high:rejects['no_constant_length_interval']+=1;continue
    L=low+fraction*(high-low);t=np.linspace(0,1,801);A,B,C,D,E,F=basis(t,u,v,a,b)
    z,dz,ddz=z_profile(t,z0,z1,rise);poses=[];bad=None
    for yaw in range(-60,61,10):
        alpha=math.radians(nominal+yaw);m=solve3(L,alpha,q)
        r=A+B*m;dr=C+D*m;dd=E+F*m;th=math.radians(-nominal)+alpha*t
        cc,ss=np.cos(th),np.sin(th)
        pts=np.column_stack([r*cc,r*ss,z])
        dp=np.column_stack([dr*cc-alpha*r*ss,dr*ss+alpha*r*cc,dz])
        ddp=np.column_stack([(dd-alpha*alpha*r)*cc-2*alpha*dr*ss,(dd-alpha*alpha*r)*ss+2*alpha*dr*cc,ddz])
        curvature=np.linalg.norm(np.cross(dp,ddp),axis=1)/np.linalg.norm(dp,axis=1)**3
        minR=1/max(float(curvature.max()),1e-20)
        if minR<required:bad='sampled_bend_radius';break
        chords=np.linalg.norm(np.diff(pts,axis=0),axis=1);arcs=np.r_[0,np.cumsum(chords)]
        second_xy=6*(hi-lo)/min(u,v)**2+2*alpha*1.875*(hi-lo)/min(u,v)+alpha*alpha*hi
        second_z=6*abs(z1-z0)/(1-rise)**2
        error=(second_xy+second_z)/((len(t)-1)**2*8)
        coarse=pts[::4];s=arcs[::4];mask=np.abs(s[:,None]-s[None,:])>math.pi*(rad+gap)
        nominal_min=float(np.linalg.norm(coarse[:,None,:]-coarse[None,:,:],axis=2)[mask].min())
        if nominal_min<2*(rad+gap):bad='sampled_nonlocal_overlap';break
        lower=nominal_min-2*chords.max()*4-2*error
        if lower<2*(rad+gap):
            vv=np.diff(pts,axis=0);ww=pts[:,None,:]-pts[:-1][None,:,:]
            tt=np.clip(np.sum(ww*vv[None,:,:],axis=2)/np.sum(vv*vv,axis=1)[None,:],0,1)
            distance=np.linalg.norm(ww-tt[:,:,None]*vv[None,:,:],axis=2)
            far=(np.abs(arcs[:,None]-arcs[:-1][None,:])>math.pi*(rad+gap))&(np.abs(arcs[:,None]-arcs[1:][None,:])>math.pi*(rad+gap))
            # Vertex-to-segment alone is not a 3D segment/segment lower bound.
            # Subtract half the maximum first-segment length as coverage.
            lower=float(distance[far].min())-chords.max()/2-2*error
            if lower<2*(rad+gap):bad='nonlocal_clearance_unresolved';break
        poses.append(dict(yaw_deg=yaw,middle_radius_mm=m,centreline_length_mm=length3(m,alpha,q),
                          sampled_minimum_curvature_radius_mm=minR,nonlocal_distance_lower_bound_mm=lower,
                          second_derivative_chord_error_bound_mm=error,curve_mm=pts.tolist()))
    if bad:rejects[bad]+=1;continue
    seeds.append(dict(nominal_angle_deg=nominal,start_radius_mm=a,end_radius_mm=b,entry_fraction=u,exit_fraction=v,
                      start_z_mm=z0,end_z_mm=z1,rise_fraction=rise,length_interval_fraction=fraction,
                      centreline_length_mm=L,poses=poses))
    print('UART_RISE_SEED',len(seeds),count,nominal,a,b,z0,z1,rise,time.time()-started,flush=True)
    if len(seeds)>=12:break
out=dict(status='PASS' if seeds else 'BLOCKED',scope='Finite rising UART group-centreline allocations only',
         source_blend_sha256=space['source_blend_sha256'],source_space_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
         source_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),members=group['members'],
         diameter_mm=rad*2,project_gap_mm=gap,required_curvature_radius_mm=required,
         candidates_tested=count,rejections=dict(rejects),selected=seeds,elapsed_s=time.time()-started,
         source_solid_checks='NOT_TESTED',inter_group='NOT_TESTED',individual_wire_lengths='NOT_TESTED',
         real_anchors='NOT_TESTED',selected_harness=False,main_geometry_changed=False,
         limits=['Unselected 26AWG catalogue sample; no actual cable or terminal is specified.',
                 'Staging endpoints are not installed retainers or connector exits.',
                 'Same group-centreline length does not prove all four wire lengths or dynamic life.',
                 '13 yaw poses and numerical curvature samples do not prove continuous behaviour.',
                 'Every seed still needs actual source-solid, other-wire and head-pose validation.'])
(HERE/('uart_rising_loops_refined.json' if REFINE else 'uart_rising_loops.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('UART_RISE_COMPLETE',out['status'],count,dict(rejects),time.time()-started,flush=True)
