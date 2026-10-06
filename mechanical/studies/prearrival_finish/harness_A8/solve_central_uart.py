"""Four fine-wire candidates in the existing central annular passage.

All four wires are rotational copies of one constant-length curve, with fixed
axial endpoints and vertical endpoint tangents. The zero-pose curve has a smooth
angular excursion to retain slack. Source-solid checks are separate.
"""
from pathlib import Path
import json,hashlib,math,time
import numpy as np
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent
receipt=HERE/'receipt.json';received=json.loads(receipt.read_text())
od=received['candidate']['od_interval_mm'][1]
R=6.8;z0,z1=150.,182.;height=z1-z0;gap=.3
wire_bend=received['candidate']['catalogue_bend_reference_mm'];required=wire_bend+od/2
S=np.array([0,0,0,10,-15,6.]);B=np.array([0,0,16,-32,16,0.])
t=np.linspace(0,1,641);nodes,weights=np.polynomial.legendre.leggauss(96);qt=(nodes+1)/2;qw=weights/2
started=time.time();results=[];chosen=None
def length(c,alpha):
    d=poly.polyval(qt,poly.polyder(alpha*S+c*B))
    return float(np.sum(qw*np.sqrt(R*R*d*d+height*height)))
def solve(L,alpha):
    lo,hi=0.,3.
    assert length(lo,alpha)<=L<=length(hi,alpha)
    for _ in range(48):
        mid=(lo+hi)/2
        if length(mid,alpha)<L:lo=mid
        else:hi=mid
    return (lo+hi)/2
def extrema_abs(co):
    roots=poly.polyroots(poly.polyder(co))
    ts=[0.,1.]+[float(x.real) for x in roots if abs(x.imag)<1e-8 and 0<x.real<1]
    return float(np.abs(poly.polyval(ts,co)).max())

for L in [33.2,33.5,34.,34.5,35.,36.,38.]:
    poses=[];failure=None
    for yaw in range(-60,61,10):
        alpha=math.radians(yaw)
        if not length(0,alpha)<=L<=length(3,alpha):failure='length_range';break
        c=solve(L,alpha);co=alpha*S+c*B
        theta=poly.polyval(t,co);d=poly.polyval(t,poly.polyder(co));dd=poly.polyval(t,poly.polyder(co,2))
        cs,sn=np.cos(theta),np.sin(theta)
        p=np.column_stack([R*cs,R*sn,z0+height*t])
        dp=np.column_stack([-R*sn*d,R*cs*d,np.full(len(t),height)])
        ddp=np.column_stack([-R*cs*d*d-R*sn*dd,-R*sn*d*d+R*cs*dd,np.zeros(len(t))])
        kappa=np.linalg.norm(np.cross(dp,ddp),axis=1)/np.linalg.norm(dp,axis=1)**3
        bend=1/float(kappa.max())
        if bend<required:failure='catalogue_bend_screen';break
        second=R*(extrema_abs(poly.polyder(co))**2+extrema_abs(poly.polyder(co,2)))
        err=second/(len(t)-1)**2/8
        poses.append(dict(yaw_deg=yaw,slack_excursion_rad=c,angular_polynomial_coefficients=co.tolist(),
            each_centreline_length_mm=length(c,alpha),sampled_minimum_bend_radius_mm=bend,
            second_derivative_chord_error_bound_mm=err,first_wire_curve_mm=p.tolist()))
    case=dict(each_segment_length_mm=L,completed_pose_count=len(poses),failure=failure)
    results.append(case)
    if not failure:chosen=dict(**case,poses=poses);break
out=dict(status='PASS' if chosen else 'BLOCKED',scope='Four independent fine-wire kinematic candidates in existing central gap only',
    source_blend_sha256=received['sources']['mechanical/mori_v1_2.blend'],source_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
    wire_od_max_mm=od,catalogue_bend_reference_mm=wire_bend,applied_bend_screen_mm=required,
    radius_from_yaw_axis_mm=R,z_endpoints_mm=[z0,z1],wire_zero_azimuths_deg=[0,90,180,270],
    wire_count=4,pinmap='H06_1, H06_2, H06_3, H06_4; no conductor removed',
    classification='PLACEHOLDER / ASSUMED routes; vendor-documented candidate wire OD only',
    geometry_changed=False,trials=results,selected=chosen,elapsed_s=time.time()-started,
    limitations=['Four paths have individually constant length at the sampled 13 yaw poses.',
        'No physical anchors, sleeves, guiding features or terminal fan-out defined.',
        'No completed connection to CAM or motion board; segment lengths are not manufacturing cut lengths.',
        'Source solids, other wires and self/inter-wire separation need a separate check.',
        'Numerical bend screening is not wire force, torsional strain or dynamic-fatigue qualification.'])
(HERE/'central_uart_curves.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A8_CENTRAL_UART',out['status'],[{k:v for k,v in row.items()} for row in results],flush=True)
