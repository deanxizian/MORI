from pathlib import Path
p=Path('/Users/dean/Documents/MORI/mechanical/studies/prearrival_finish/harness_A8/check_CAM_lift2_forming_packing.py');__file__=str(p)
exec(compile(p.read_text().split('\nfor fraction in np.linspace',1)[0],str(p),'exec'),globals())
base,u,error=fc_curve(.8);a=fine(base,.01);b=pw_fans[1];r=pair(a,b,error,pw_fan_errors[1]);i,j=r['sample_indices']
d=float(np.linalg.norm(a[0][i]-b[0][j]));upper=d+error+pw_fan_errors[1]
w={'status':'FAIL' if upper<OD else 'NOT_TESTED','scope':'Physical wire-envelope witness in nominal prescribed curves, not real measured wire',
 'source_main_sha256':source_hash,'source_packing_sha256':sha(L2_OUT/'packing_screen.json'),'fraction':.8,'wire_slot':0,'upstream_slot':1,
 'wire_point_mm':a[0][i].tolist(),'upstream_point_mm':b[0][j].tolist(),'sample_centre_distance_mm':d,
 'point_uncertainty_mm':error+pw_fan_errors[1],'upper_bound_actual_centre_distance_mm':upper,'combined_radii_mm':OD,
 'main_applied':False,'whole_harness':'BLOCKED'}
(L2_OUT/'packing_collision_witness.json').write_text(json.dumps(w,indent=2)+'\n');print(json.dumps(w),flush=True)
