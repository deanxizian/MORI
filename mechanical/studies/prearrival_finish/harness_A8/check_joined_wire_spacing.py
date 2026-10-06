"""Numerical/analytic wire-to-wire screening independent of changed solids."""
from pathlib import Path
import json,math,hashlib,itertools
import numpy as np
from numpy.polynomial import polynomial as poly
HERE=Path(__file__).resolve().parent
path=HERE/'joined_entry_screen.json';d=json.loads(path.read_text())
central_path=HERE/'central_uart_curves.json';central=json.loads(central_path.read_text())
old={p['yaw_deg']:p for p in central['selected']['poses']}
radius=d['wire_od_mm']/2;gap=.3
inter=[];self_checks=[];lengths=[];outer=[]
for yaw in range(-60,61,10):
    rows=[r for r in d['rows'] if r['yaw_deg']==yaw]
    co=poly.polyder(old[yaw]['angular_polynomial_coefficients'])
    roots=poly.polyroots(poly.polyder(co))
    ts=[0.,1.]+[float(r.real) for r in roots if abs(r.imag)<1e-8 and 0<r.real<1]
    max_angular_per_z=float(np.max(np.abs(poly.polyval(ts,co))))/32
    # On the approaches azimuth is constant; therefore this Lipschitz bound
    # applies to the full joined curve as a function of Z, including the flat
    # body tail (same angle at all its radii). All radii are at least6.8mm.
    for a,b in itertools.combinations(d['wire_azimuths_deg'],2):
        angle=math.radians(min(abs(a-b),360-abs(a-b)))
        dz=np.linspace(0,min(70,angle/max_angular_per_z),4001)
        bounds=np.minimum(dz,13.6*np.sin(np.maximum(0,angle-max_angular_per_z*dz)/2))
        centre=float(bounds.max());surface=centre-2*radius
        inter.append(dict(yaw_deg=yaw,wires_deg=[a,b],status='PASS' if surface>=gap else 'FAIL',
            centre_distance_lower_bound_mm=centre,surface_distance_lower_bound_mm=surface,
            method='All-parameter axial/angular bound on rotational copies; r>=6.8'))
    row=rows[0];pts=np.asarray(row['curve_mm']);ds=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    cum=np.r_[0,np.cumsum(ds)];cutoff=2.0
    best=(float('inf'),None)
    for i in range(len(pts)):
        j=np.searchsorted(cum,cum[i]+cutoff)
        if j>=len(pts):continue
        dist=np.linalg.norm(pts[j:]-pts[i],axis=1);k=int(np.argmin(dist))
        if dist[k]<best[0]:best=(float(dist[k]),[i,int(j+k)])
    coverage=float(ds.max())+2*row['error_bound_mm']
    surface=best[0]-coverage-2*radius
    self_checks.append(dict(yaw_deg=yaw,status='PASS' if surface>=gap else 'FAIL',
        sampled_nonlocal_arc_cutoff_mm=cutoff,minimum_sample_centre_distance_mm=best[0],
        sample_coverage_deduction_mm=coverage,screened_surface_gap_lower_bound_mm=surface,
        pair_indices=best[1],scope='Nonlocal sampled pairs; immediate neighbourhood relies on analytic tangent continuity and bend screen'))
    for r in rows:
        lengths.append(dict(yaw_deg=yaw,azimuth_deg=r['azimuth_deg'],
            analytic_staging_length_mm=r['analytic_total_staging_length_mm'],
            minimum_bend_screen_mm=min(r['minimum_sampled_central_bend_mm'],r['analytic_approach_bend_radius_mm'])))
seed_path=HERE.parent/'head_harness/split_planar_loops_refined.json'
for group in json.loads(seed_path.read_text())['groups']:
    if group['status']!='PASS':continue
    bound=min(group['centre_radius_bounds_mm'])-32-radius-group['diameter_mm']/2
    outer.append(dict(group=group['id'],surface_gap_lower_bound_mm=bound,
                      status='PASS' if bound>=gap else 'BLOCKED',method='Global radial slabs; joined route r<=32mm'))
ok=all(r['status']=='PASS' for r in inter+self_checks+outer)
result=dict(status='PASS' if ok else 'BLOCKED',scope='Four joined staging wires only, not installed complete harness',
    source_route_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    interwire_checks=inter,self_checks=self_checks,outer_loop_checks=outer,length_and_bend=lengths,
    minimum_interwire_surface_bound_mm=min(r['surface_distance_lower_bound_mm'] for r in inter),
    minimum_sampled_self_surface_bound_mm=min(r['screened_surface_gap_lower_bound_mm'] for r in self_checks),
    minimum_bend_mm=min(r['minimum_bend_screen_mm'] for r in lengths),
    staging_length_spread_mm=float(np.ptp([r['analytic_staging_length_mm'] for r in lengths])),
    physical_guiding_and_endpoint_retention='NOT_TESTED',dynamic_fatigue='NOT_TESTED',supplier_cut_length='BLOCKED')
(HERE/'joined_wire_spacing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k.startswith('minimum_') or k in ['status','staging_length_spread_mm']},indent=2))
