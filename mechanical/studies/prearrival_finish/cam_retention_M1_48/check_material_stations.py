"""Track positions along each unchanged curve through all stored poses.

A constant total length alone is insufficient if fixed clamps slide along the
material. This checks cumulative length and direction at the proposed clamps,
plus the two currently unrestrained neck-service boundaries.
"""
from pathlib import Path
import sys,json,itertools,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from current_context import RetentionContext,PROJECT,np,sha,pose
ctx=RetentionContext();started=time.time();A8=HERE.parent/'harness_A8'
fanfile=A8/'cam_fan_in/four_bend_transition/curves.npz'
tailfile=A8/'cam_fan_in/short_tail_v2/tails.npz'
bodyfile=A8/'cam_pitch_port/lower_staging/body_partial_curves.npz'
fan=np.load(fanfile);tails=np.load(tailfile);body=np.load(bodyfile)
lawfile=A8/'central_uart_curves.json';law=json.loads(lawfile.read_text())
laws={r['yaw_deg']:r['angular_polynomial_coefficients'] for r in law['selected']['poses']}
stations=[]
for pin in range(1,5):
    q=body[f'pin{pin}_yaw0']
    def zpoint(z):
        ids=np.flatnonzero(abs(q[:,2]-z)<1e-7);assert len(ids)==1,(pin,z,len(ids))
        return q[ids[0]].copy()
    port=ctx.ctx.port_pins['motion_J5']['pins'][str(pin)].copy()
    yaw=fan[f'pin{pin}_candidate0'][-1].copy();yaw[2]=232.
    connector=tails[f'slot{pin-1}'][0].copy();connector[2]=212.
    for name,group,point,mode in [
        ('body_port','body',port,'connector datum only; no separate strain relief'),
        ('neck_body_boundary','body',zpoint(147.),'curve boundary; not a clamp'),
        ('neck_yaw_boundary','yaw',zpoint(179.),'curve boundary; not a clamp'),
        ('yaw_anchor','yaw',yaw,'proposed integral support/tie'),
        ('CAM_anchor','pitch',connector,'proposed integral support/tie'),
        ('CAM_port','pitch',tails[f'slot{pin-1}'][0].copy(),'mating allocation; not physically confirmed')]:
        stations.append(dict(pin=pin,name=name,group=group,point_zero_mm=point.tolist(),mode=mode))

rows=[]
for station in stations:
    samples=[]
    for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
        p=ctx.curves[f'pin{station["pin"]}_y{yaw}_p{pitch}']
        mat=pose(station['group'],yaw,pitch);target=mat[:3,:3]@station['point_zero_mm']+mat[:3,3]
        vectors=np.diff(p,axis=0);ds=np.linalg.norm(vectors,axis=1)
        t=np.clip(np.einsum('ij,ij->i',target-p[:-1],vectors)/(ds*ds),0.,1.)
        projected=p[:-1]+vectors*t[:,None];dist=np.linalg.norm(projected-target,axis=1);i=int(dist.argmin())
        arc=float(ds[:i].sum()+t[i]*ds[i]);direction=(vectors[i]/ds[i])@mat[:3,:3]
        direction/=np.linalg.norm(direction)
        tangent_basis='Straight sampled segment in station frame'
        # The service boundary falls at an arc join. A one-sided chord rotates
        # with the nearby curvature and is not the endpoint tangent. Check the
        # original angular law derivative instead of loosening its tolerance.
        chord_direction=direction.copy()
        if station['name'] in ['neck_body_boundary','neck_yaw_boundary']:
            parameter=0. if station['name']=='neck_body_boundary' else 1.
            derivative=float(np.polynomial.polynomial.polyval(parameter,np.polynomial.polynomial.polyder(laws[yaw])))
            assert abs(derivative)<1e-10
            direction=np.array([0.,0.,1.])
            tangent_basis='Analytic central theta derivative is zero at endpoint; adjacent retained circular bend tangent is +Z'
        samples.append(dict(yaw_deg=yaw,pitch_deg=pitch,curve_distance_mm=float(dist[i]),
                            material_s_from_body_mm=arc,tangent_in_station_frame=direction.tolist(),
                            chord_direction_diagnostic=chord_direction.tolist(),tangent_basis=tangent_basis))
    arcs=[r['material_s_from_body_mm'] for r in samples]
    tangents=np.asarray([r['tangent_in_station_frame'] for r in samples])
    reference=tangents[next(i for i,r in enumerate(samples) if r['yaw_deg']==r['pitch_deg']==0)]
    spread=float(np.degrees(np.arccos(np.clip(tangents@reference,-1,1))).max())
    delta=max(arcs)-min(arcs);error=max(r['curve_distance_mm'] for r in samples)
    rows.append({**station,'status':'PASS' if delta<.001 and error<.001 and spread<.2 else 'BLOCKED',
                 'minimum_material_s_mm':min(arcs),'maximum_material_s_mm':max(arcs),
                 'material_position_variation_mm':delta,'maximum_target_error_mm':error,
                 'maximum_tangent_deviation_deg':spread,'samples':samples})
    print('MATERIAL_STATION',station['pin'],station['name'],delta,error,spread,rows[-1]['status'],flush=True)
ctx.assert_unchanged()
result=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite-pose numerical material coordinate and local direction compatibility, not physical grip or wire equilibrium',
    **ctx.evidence(),script_sha256=sha(__file__),context_sha256=sha(HERE/'current_context.py'),
    sources={str(p.relative_to(PROJECT)):sha(p) for p in [fanfile,tailfile,bodyfile,lawfile]},
    stations=rows,poses_per_station=130,numerical_material_comparison_tolerance_mm=.001,
    numerical_tangent_comparison_tolerance_deg=.2,
    physical_length_tolerance='NOT_DEFINED',neck_boundary_restraints='NOT_TESTED',
    physical_slip_pullout_and_flex='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'material_stations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('MATERIAL_STATIONS_DONE',result['status'],flush=True)
