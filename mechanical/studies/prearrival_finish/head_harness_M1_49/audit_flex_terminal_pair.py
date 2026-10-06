"""Apply received CAM and original LCD outlet directions to prior end budgets."""
from pathlib import Path
import hashlib,json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex/connector_faces'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
receipt=OUT/'direction_receipt.json';data=read(receipt);assert data['status']=='PASS'
assert data['directions']['DISPLAY_FPC_18']['outward_zero_pose_XYZ']==[-1,0,0]
assert data['LCD_direction']['supported_exit_zero_pose_XYZ']==[-1,0,0]
prior=OUT/'terminal_length_audit.json';assert read(prior)['status']=='FAIL'
rows=[]
for radius in [5.,7.5]:
    one=math.pi*radius
    rows.append(dict(assumed_minimum_radius_mm=radius,
        each_end_necessary_length_mm=one,both_ends_necessary_length_mm=2*one,
        each_end_budget_mm=15,total_end_budget_mm=30,
        each_end_shortfall_lower_bound_mm=one-15,
        central_length_upper_bound_ignoring_other_constraints_mm=200-2*one,
        status='FAIL'))
result=dict(status='FAIL',scope='Old 170+15+15 allocation cannot meet both supported inlet tangents at the stated R assumptions',
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [receipt,prior,HERE/'static_flex_geometry.py']},
    orientation_along_cable='CAM to LCD',
    CAM_outward_tangent=[-1,0,0],core_initial_tangent=[1,0,0],
    core_final_tangent=[-1,0,0],LCD_insertion_tangent=[1,0,0],
    minimum_tangent_turn_each_end_rad=math.pi,cases=rows,
    assumptions=['R5/R7.5 are prior capacity assumptions, not vendor limits.',
        'No allowance is included for insertion, stiffeners, positional offsets or strip twist.',
        'Upper bounds on center length are necessary conditions only, not passing routes.',
        'No conclusion that the original 200 mm cable cannot fit.'],
    main_changed=False,full_LCD_route='BLOCKED',script_sha256=sha(Path(__file__)))
(OUT/'pair_terminal_length_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FFC_PAIR_TERMINAL_AUDIT_DONE',result['status'])
