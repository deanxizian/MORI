"""Whole-span curvature and arclength bounds for the shifted CAM tails.

For the unit-speed planar base and lateral quintic offset x(s), curvature is
sqrt((1+x'^2)/R^2+x''^2)/(1+x'^2)^(3/2) on the circular span, and
abs(x'')/(1+x'^2)^(3/2) on the straight spans. Polynomial extrema bound every
subinterval; this is not a sample-only minimum-radius assertion.
"""
from pathlib import Path
import json,math,hashlib
import numpy as np
TAIL_MATH_SCRIPT=Path(__file__).resolve();TAIL_MATH_OUT=TAIL_MATH_SCRIPT.parent/'cam_parallel_pitch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report_path=TAIL_MATH_OUT/'shifted_tail_screen.json';report=json.loads(report_path.read_text())
assert report['status']=='PASS'
r=report['selected'];radius=r['radius_mm'];shift=r['shift_x_mm'];length=r['shift_length_mm']
turn_end=math.pi*radius/(2*length)
derivative=lambda u:30*shift/length*u*u*(1-u)**2
second=lambda u:60*shift/(length*length)*u*(1-u)*(1-2*u)
def extrema(lo,hi):
    d=[derivative(u) for u in [lo,hi]+([.5] if lo<=.5<=hi else [])]
    dd=[abs(second(u)) for u in [lo,hi]+[v for v in [(3-math.sqrt(3))/6,(3+math.sqrt(3))/6] if lo<=v<=hi]]
    return max(0.,min(d)-1e-12),max(d)+1e-12,max(dd)+1e-12
knots=sorted(set(np.linspace(0.,1.,4097).tolist()+[turn_end]))
minimum=math.inf;low_length=0.;high_length=0.;limiting=None
for lo,hi in zip(knots,knots[1:]):
    dmin,dmax,ddmax=extrema(lo,hi)
    acc_circular=1/radius if hi<=turn_end+1e-14 else 0.
    cross_max=math.sqrt((1+dmax*dmax)*acc_circular**2+ddmax*ddmax)
    lower=(1+dmin*dmin)**1.5/cross_max if cross_max>0 else math.inf
    if lower<minimum:minimum=lower;limiting=[lo,hi]
    low_length+=(hi-lo)*length*math.sqrt(1+dmin*dmin)
    high_length+=(hi-lo)*length*math.sqrt(1+dmax*dmax)
curve_path=TAIL_MATH_OUT/'shifted_tails.npz';a=np.load(curve_path)
base_total=float(a['arc_parameter_mm'][-1]);remaining=base_total-length
low_length+=remaining;high_length+=remaining
polyline_lengths=[float(np.linalg.norm(np.diff(a[f'slot{i}'],axis=0),axis=1).sum()) for i in range(4)]
res={'status':'PASS' if minimum>=report['required_radius_mm'] and high_length-low_length<.001 else 'BLOCKED',
     'scope':'Entire analytic CAM fixed-tail spans only; nominal pose-independent shape',
     'script_sha256':sha(TAIL_MATH_SCRIPT),'source_report_sha256':sha(report_path),'source_curves_sha256':sha(curve_path),
     'minimum_curvature_radius_lower_bound_mm':minimum,'minimum_required_mm':report['required_radius_mm'],
     'limiting_shift_parameter_interval':limiting,'subinterval_count':len(knots)-1,
     'length_lower_mm':low_length,'length_upper_mm':high_length,'length_interval_width_mm':high_length-low_length,
     'polyline_lengths_mm':polyline_lengths,'physical_dynamic_bend_life':'NOT_TESTED',
     'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False}
(TAIL_MATH_OUT/'tail_math_bounds.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(res,ensure_ascii=False))
