"""Find explicit geometric witnesses, without changing clearance thresholds."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'contact_with_upper_wires'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pathfile=REST/'contact_continuous/path.npz';curvefile=BASE/'cam_side_fans/c6_join/candidate_curves.npz'
arrivalfile=REST/'wire_body_arrival_refined/state.npz'
path=np.load(pathfile);curves=np.load(curvefile);arrival=np.load(arrivalfile)
names=['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']
lo=np.array([-1.04,-.75,0.]);hi=np.array([1.04,.75,5.7]);rows=[]
for name in names:
    p=curves[name+'_y0'];radius=.4445 if name.startswith('SPK_') else .5842;best=None
    for i,(rear,rotation) in enumerate(zip(path['rear_mm'],path['rotations'])):
        ids=np.flatnonzero(np.all(abs(p-rear)<[7.,7.,7.],axis=1))
        if len(ids)==0:continue
        local=(p[ids]-rear)@rotation
        delta=np.maximum(np.maximum(lo-local,local-hi),0.);d=np.linalg.norm(delta,axis=1)
        k=int(np.argmin(d));gap=float(d[k]-radius)
        if best is None or gap<best['sampled_surface_gap_mm']:
            closest_local=np.minimum(np.maximum(local[k],lo),hi)
            best=dict(path_index=i,terminal_rear_mm=rear.tolist(),wire_point_mm=p[ids[k]].tolist(),
                      box_closest_point_mm=(closest_local@rotation.T+rear).tolist(),wire_radius_mm=radius,
                      centre_inside_box=bool(d[k]<1e-9),sampled_surface_gap_mm=gap,
                      gap_upper_bound_with_curve_error_mm=gap+.0003+2e-5)
    rows.append(dict(wire=name,best_observed=best,
                     clearance_status='FAIL' if best and best['gap_upper_bound_with_curve_error_mm']<.3 else 'NOT_TESTED'))

# A local pair witness suffices to refute clearance. This intentionally does
# not certify a global minimum or prove failure of any different route.
reference=json.loads((REST/'wire_body_arrival_refined/review.json').read_text())
w=np.array(reference['row']['wire_pairs'][0]['point_mm']);a=arrival['arrival_wire'];b=curves['P_J18_2_y0']
a=a[np.linalg.norm(a-w,axis=1)<5];b=b[np.linalg.norm(b-w,axis=1)<5];assert len(a) and len(b)
best=None
for start in range(0,len(a),128):
    d=np.linalg.norm(a[start:start+128,None,:]-b[None,:,:],axis=2);i,j=np.unravel_index(np.argmin(d),d.shape)
    value=float(d[i,j])
    if best is None or value<best['centre_distance_mm']:
        best=dict(cam_point_mm=a[start+i].tolist(),neighbor_point_mm=b[j].tolist(),centre_distance_mm=value,
                  sampled_surface_gap_mm=value-.3302-.5842,
                  surface_gap_upper_bound_with_curve_error_mm=value-.3302-.5842+.0003*2+2e-5)
best['clearance_status']='FAIL' if best['surface_gap_upper_bound_with_curve_error_mm']<.3 else 'NOT_TESTED'
assert any(r['clearance_status']=='FAIL' for r in rows)
result=dict(status='PASS',scope='Explicit collision/clearance diagnosis, not route release or global-minimum certification',
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [pathfile,curvefile,arrivalfile,REST/'wire_body_arrival_refined/review.json']},
    continuous_path_sample_witnesses=rows,arrival_pair_witness=best,
    main_changed=False,full_harness='BLOCKED',script_sha256=sha(Path(__file__)),actual_command=[sys.executable,*sys.argv])
(OUT/'explicit_witnesses.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_NEIGHBOR_WITNESSES_DONE',json.dumps(result['arrival_pair_witness']))
for row in rows:
    if row['clearance_status']=='FAIL':print(row['wire'],row['best_observed'])
