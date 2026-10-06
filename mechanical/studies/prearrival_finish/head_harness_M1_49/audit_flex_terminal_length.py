"""Necessary terminal-length condition for the earlier capacity-only ribbon.

This is conditional on the apparent original LCD CAD cable entry direction.
It neither assigns vendor bend limits nor proves every 200 mm route impossible.
"""
from pathlib import Path
import hashlib,json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex';OUT=BASE/'connector_faces'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
core=BASE/'review/review.json';ports=BASE/'endpoints.json';faces=OUT/'review.json'
r=json.loads(core.read_text());assert r['status']=='PASS'
assert r['parameters']['analytic_length_mm']==170
assert r['parameters']['unmodeled_end_approach_reserve_mm']==[15,15]
cad=ROOT/'mechanical/sources/v1_2_verified_dimensions/1.85inch_touch_lcd_module-3d.stp'
assert sha(cad)=='da8b3fca5ffd30c89d12bf488203741baaa1bd390732b62d92b23b279fb1dd9d'
report=dict(status='FAIL',scope='Conditional endpoint-length audit of the 170 mm central capacity sample',
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [core,ports,faces,cad,HERE/'static_flex_geometry.py']},
    central_end_tangent_world=[-1,0,0],LCD_insertion_tangent_world=[1,0,0],
    tangent_evidence='Original vendor STEP Connector_108 appears to enter from world -X. Actual contact face, pin1 and purchased revision remain unqualified.',
    minimum_total_tangent_turn_rad=math.pi,reserved_LCD_end_length_mm=15,
    method='For curvature <= 1/R, rotating the oriented unit tangent by pi requires arc length >= pi*R. This necessary condition also applies to a 3D centerline. Endpoint distances, insertion length and twist constraints can only add further restrictions.',
    radii_are_capacity_assumptions_not_vendor_limits=True,
    cases=[dict(minimum_radius_mm=q,necessary_length_lower_bound_mm=math.pi*q,
        budget_shortfall_lower_bound_mm=math.pi*q-15,status='FAIL') for q in [5.,7.5]],
    full_route='BLOCKED',main_changed=False,
    limitations=['This rejects the old fixed 15 mm terminal budget under the stated R assumptions.',
        'It is not a conclusion that the original 200 mm cable is too short or cannot fit.',
        'Reallocate center and end lengths and regenerate a complete candidate after connector-direction reconciliation.'],
    script_sha256=sha(Path(__file__)))
(OUT/'terminal_length_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FFC_TERMINAL_LENGTH_AUDIT_DONE',report['status'])
