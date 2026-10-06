"""Analytic bounds across the complete -20..25 degree pitch interval.

This proves nominal curve lengths, circle radii, and positive straight spans.
Collision checks are separately finite-pose; no continuous collision or cable
mechanics claim is made by this analytic calculation.
"""
from pathlib import Path
import json,math,hashlib
import numpy as np
ARC_MATH_SCRIPT=Path(__file__).resolve();ARC_MATH_ROOT=ARC_MATH_SCRIPT.parent
OUT=ARC_MATH_ROOT/'cam_parallel_pitch/following_arc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=OUT/'screen.json';d=json.loads(src.read_text());assert d['status']=='PASS'
tail=np.load(ARC_MATH_ROOT/'cam_parallel_pitch/shifted_tails.npz')['slot0'][-1]
head_z=222.;y0=float(tail[1]);dz=float(tail[2])-head_z
lo=math.radians(-20);hi=math.radians(25)
def bounds(k0,kc,ks,kl):
    candidates=[lo,hi];R=math.hypot(kc,ks)
    if R>0 and abs(kl)<=R:
        phi=math.atan2(ks,-kc);u=math.asin(-kl/R)
        for k in range(-3,4):
            for root in [u+2*math.pi*k,math.pi-u+2*math.pi*k]:
                p=root-phi
                if lo<p<hi:candidates.append(p)
    values=[k0+kc*math.cos(p)+ks*math.sin(p)+kl*p for p in candidates]
    return {'lower_mm':min(values)-1e-9,'upper_mm':max(values)+1e-9,'critical_pitch_deg':[math.degrees(p) for p in candidates]}
rows=[]
for i,r in enumerate(d['selected']):
    p=r['parameters'];ay=p['anchor_y_mm'];az=p['anchor_z_mm'];rb=p['lower_radius_mm'];end=p['terminal_straight_mm'];target=r['exact_length_mm']
    A=y0+end;B=-dz-rb
    C0=math.pi*rb-math.pi*ay/2+az-head_z+end
    Cc=math.pi*A/2+B;Cs=math.pi*B/2-A
    radius=bounds((rb-ay)/2,A/2,B/2,0.)
    height=bounds((target-C0)/2,-Cc/2,-Cs/2,rb/2)
    vertical=bounds(az+(target-C0)/2-head_z,B-Cc/2,-A-Cs/2,rb/2)
    discrepancies=[]
    for q in r['poses']:
        angle=math.radians(q['pitch_deg']);base=C0+Cc*math.cos(angle)+Cs*math.sin(angle)-rb*angle
        h=(target-base)/2;rt=(rb-ay+A*math.cos(angle)+B*math.sin(angle))/2
        span=az+h-head_z-A*math.sin(angle)+B*math.cos(angle)
        discrepancies.extend([abs(h-q['upper_arc_lift_mm']),abs(rt-q['top_radius_mm']),abs(span-q['vertical_span_mm'])])
    ok=min(radius['lower_mm'],rb)>=d['minimum_radius_required_mm'] and height['lower_mm']>=5. and vertical['lower_mm']>=.5 and max(discrepancies)<.0001
    rows.append({'candidate':i,'status':'PASS' if ok else 'BLOCKED','upper_radius':radius,'lower_radius_mm':rb,
        'start_straight':height,'column_straight':vertical,'end_straight_mm':end,'exact_service_length_mm':target,
        'length_identity':'L(p) = base(p) + 2 * (target - base(p))/2 = target',
        'maximum_difference_to_float_matrix_pose_records_mm':max(discrepancies),
        'parameter_domain_degrees':[-20,25],'joins':'C1 tangent continuity; curvature jumps at circle/line joins'} )
res={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED','rows':rows,
    'script_sha256':sha(ARC_MATH_SCRIPT),'source_screen_sha256':sha(src),
    'source_tail_sha256':sha(ARC_MATH_ROOT/'cam_parallel_pitch/shifted_tails.npz'),
    'scope':'Analytic lengths, radius and positive-span bounds for every pitch angle; no continuous collision proof',
    'continuous_collision':'NOT_TESTED','physical_cable_behavior':'NOT_TESTED','whole_harness':'BLOCKED',
    'main_applied':False,'manufacturing_release':False}
(OUT/'math_bounds.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':res['status'],'rows':rows},ensure_ascii=False))
