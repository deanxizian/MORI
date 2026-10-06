"""Match retained curve evidence and bound the complete central angular law.

Mathematical source bounds are reusable when the exact source curves match.
No old source-solid clearance or physical cable qualification is inherited.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];A8=HERE.parent/'harness_A8'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
sources={}
def received(relative):
    path=A8/relative;sources[str(path.relative_to(PROJECT))]=sha(path)
    return read(path)
body=received('body_prefix_v2/packing.json')
central=received('central_uart_curves.json')
fan=received('cam_fan_in/four_bend_transition/math_bounds.json')
pool=received('cam_fan_in/four_bend_transition/pool.json')
pitch=received('cam_fan_in/short_tail_v2/math_bounds.json')
screen=received('cam_fan_in/short_tail_v2/screen.json')
tail=received('cam_parallel_pitch/tail_math_bounds.json')
joins=received('cam_fan_in/joins.json')
for rel,expected in [('cam_pitch_port/lower_staging/body_partial_curves.npz',pool['source_body_prefix_sha256']),
                     ('cam_fan_in/four_bend_transition/curves.npz',pool['curves_sha256']),
                     ('cam_fan_in/short_tail_v2/curves.npz',screen['curves_sha256']),
                     ('cam_fan_in/short_tail_v2/tails.npz',screen['tail_curves_sha256']),
                     ('cam_parallel_pitch/shifted_tails.npz',tail['source_curves_sha256'])]:
    path=A8/rel;assert sha(path)==expected
    sources[str(path.relative_to(PROJECT))]=expected
assert fan['source_pool_sha256']==sha(A8/'cam_fan_in/four_bend_transition/pool.json')
assert pitch['source_screen_sha256']==sha(A8/'cam_fan_in/short_tail_v2/screen.json')
assert joins['fan_assignment']==[0,0,0,0]
for path,expected in joins['files'].items():assert sha(PROJECT/path)==expected
body_curves=np.load(A8/'cam_pitch_port/lower_staging/body_partial_curves.npz')
for row in body['selected']:
    first=np.asarray(row['curve_mm'])
    for yaw in range(-60,61,10):
        assert np.allclose(body_curves[f'pin{row["pin"]}_yaw{yaw}'][:len(first)],first,atol=1e-8,rtol=0)
    assert min(row['entry_bend_radius_mm'],row['exit_bend_radius_mm'],row['planar_path']['radius_mm'])>=7.

def abs_bound(coefficients):
    roots=poly.polyroots(poly.polyder(coefficients))
    ts=[0.,1.]+[float(x.real) for x in roots if abs(x.imag)<1e-8 and 0<x.real<1]
    # Outward allowance on the low-degree floating-point polynomial extrema.
    return float(np.abs(poly.polyval(ts,coefficients)).max())+1e-8

R=central['radius_from_yaw_axis_mm'];H=32.;central_rows=[]
for row in central['selected']['poses']:
    c=row['angular_polynomial_coefficients'];w=abs_bound(poly.polyder(c));a=abs_bound(poly.polyder(c,2))
    # |r'| >= H; |r' x r''|^2 = R^2 H^2 (theta''^2+theta'^4)+R^4 theta'^6.
    lower=H**3/(R*math.sqrt(H*H*(a*a+w**4)+R*R*w**6))-1e-7
    t=np.linspace(0,1,641);theta=poly.polyval(t,c)
    analytic=np.column_stack([R*np.cos(theta),R*np.sin(theta),147+H*t])
    for selected in body['selected']:
        phi=math.radians(selected['azimuth_deg']);co,si=math.cos(phi),math.sin(phi)
        rz=np.array([[co,-si,0],[si,co,0],[0,0,1.]])
        expected=analytic@rz.T
        saved=body_curves[f'pin{selected["pin"]}_yaw{row["yaw_deg"]}']
        ids=np.flatnonzero(np.linalg.norm(saved-expected[0],axis=1)<1e-7)
        assert len(ids)==1
        assert np.allclose(saved[ids[0]:ids[0]+len(expected)],expected,atol=1e-7,rtol=0)
    central_rows.append(dict(yaw_deg=row['yaw_deg'],whole_parameter_radius_lower_mm=lower,
                             theta_prime_abs_upper=w,theta_second_abs_upper=a))
fan_rows=[r for r in fan['rows'] if r['candidate']==0]
minimum=min(7.,8.,min(r['whole_parameter_radius_lower_mm'] for r in central_rows),
            min(r['minimum_radius_lower_mm'] for r in fan_rows),
            pitch['rows'][0]['upper_radius']['lower_mm'],pitch['rows'][0]['lower_radius_mm'],
            tail['minimum_curvature_radius_lower_bound_mm'])
report=dict(status='PASS' if minimum>=6.9342 else 'BLOCKED',
    scope='Exact curve-source matching and retained whole-span radius bounds; central law newly bounded at 13 yaw values',
    minimum_radius_lower_mm=minimum,required_radius_mm=6.9342,central=central_rows,
    body_prefix_radius_mm=7.,neck_entry_exit_radius_mm=8.,
    inherited_fan_bounds=fan_rows,inherited_pitch_bounds=pitch['rows'],
    inherited_tail_radius_lower_mm=tail['minimum_curvature_radius_lower_bound_mm'],
    maximum_source_seam_error_mm=joins['maximum_endpoint_error_mm'],
    source_tangent_scope=joins['tangent_scope'],sources=sources,script_sha256=sha(__file__),
    continuous_between_yaw_values='NOT_TESTED',physical_dynamic_bend_life='NOT_TESTED',
    retention='NOT_TESTED',whole_harness='BLOCKED',main_applied=False)
(HERE/'radius_evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('RADIUS_EVIDENCE',report['status'],minimum,flush=True)
