"""Cross-check the continuous solver's evaluator and displacement formulas.

The finite derivative audit is a regression diagnostic, not the mathematical
proof. The continuous report relies on the documented integral bound.
"""
from pathlib import Path
FB_SCRIPT=Path(__file__).resolve();FB_ROOT=FB_SCRIPT.parent
FB_HELPER=FB_ROOT/'check_CAM_forming_continuous.py';__file__=str(FB_HELPER)
exec(compile(FB_HELPER.read_text().split('\ntry:\n    fc_interval',1)[0],str(FB_HELPER),'exec'),globals())
__file__=str(FB_SCRIPT)
fb_started=time.time();fb_shape=[];fb_speed=[]
for fraction in np.linspace(0.,1.,51):
    fraction=float(fraction);p,u,e=fc_curve(fraction);q,v,qe,_=fr_curve(fraction,fc_amplitude)
    interpolated=np.column_stack([np.interp(v,u,p[:,i]) for i in range(3)])
    delta=float(np.linalg.norm(interpolated-q,axis=1).max())
    ends=float(np.linalg.norm(p[[0,-1]]-q[[0,-1]],axis=1).max())
    fb_shape.append({'fraction':fraction,'maximum_difference_mm':delta,'allowed_chord_error_mm':e+1e-8,'end_error_mm':ends})
    assert delta<=e+1e-8 and ends<1e-8
for fraction in np.linspace(.0001,.9999,51):
    fraction=float(fraction);epsilon=.00001;a=fraction-epsilon;b=fraction+epsilon
    p,u,ep=fc_curve(a);q,v,eq=fc_curve(b);s=np.linspace(0.,fc_end,501)
    pa=np.column_stack([np.interp(s,u,p[:,i]) for i in range(3)])
    pb=np.column_stack([np.interp(s,v,q[:,i]) for i in range(3)])
    numerical=np.linalg.norm(pb-pa,axis=1)/(2*epsilon)
    velocity=fc_speed(s,a,b);interpolation_error=(ep+eq)/(2*epsilon)+.0001
    residual=float((numerical-velocity-interpolation_error).max())
    fb_speed.append({'fraction':fraction,'largest_estimate_minus_bound_mm':residual,'interpolation_velocity_uncertainty_mm':interpolation_error})
    assert residual<=1e-7
report={'status':'PASS','scope':'Finite diagnostic of curve identity and analytic velocity bound; not a substitute for continuous proof',
 'source_main_sha256':source_hash,'script_sha256':sha(FB_SCRIPT),'helper_sha256':sha(FB_HELPER),
 'planar_segment_lengths_mm':fr_lengths,'planar_turns_rad':fm_angles,'maximum_temporary_lift_mm':fc_amplitude,
 'upper_bend_radius_mm':fc_R,'lower_bend_radius_mm':fc_r,'fixed_lower_turn_starts_mm':[fc_B,fc_C],
 'shape_checks':fb_shape,'velocity_diagnostics':fb_speed,
 'material_length_argument':'YZ derivative has unit norm for fixed u; X(u) is unchanged. The total interval in u stays fixed, hence integral sqrt(1+Xprime^2) is independent of forming fraction.',
 'bound_argument':'Theta is the sum of three clipped ramps. The two lower ramps have fixed starts. Only the upper ramp shifts with H=h0+A*sin(pi*f); |theta_f| <= Theta(u,Hmin)+b*sup|Hprime|/R on the upper arc. Integrating this bound from0 to u bounds point velocity.',
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fb_started}
(FC_OUT/'math_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_MATH_AUDIT_DONE',len(fb_shape),len(fb_speed),flush=True)
