"""Independently audit endpoint/tangent/curve identity for the expanded pool."""
from pathlib import Path
import json,hashlib,time
import numpy as np
from numpy.polynomial import polynomial as poly
root=Path(__file__).resolve().parent;project=root.parents[3]
pool_file=root/'imu_axial_complete_assembly_pools.json'
ep_file=root/'imu_endpoints.json';wire_file=root/'ecowire_sources.json'
data=json.loads(pool_file.read_text());ep=json.loads(ep_file.read_text())
wire=next(p for p in json.loads(wire_file.read_text())['products'] if p['part_number']=='6711')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=project/'mechanical/mori_v1_2.blend';source_hash=sha(main)
assert data['source_blend_sha256']==ep['source_blend_sha256']==source_hash
assert sha(project/wire['source_file'])==wire['source_sha256']
code=(root/'imu_individual_routes.py').read_text();sample_t=np.linspace(0,1,65)
exec(code[code.index('def bezier'):code.index('def check_points')],globals())
rows=[];start=time.time()
for pin,pool in data['pools'].items():
    failures=[];minimum_radius=float('inf');max_endpoint_error=0.;max_reconstruction_error=0.
    for i,row in enumerate(pool):
        checks={};controls=list(map(np.asarray,row['cubic_controls_mm']))
        points=np.asarray(row['curve_mm']);ea=np.asarray(ep['ports']['motion_J4']['pins'][pin]);eb=np.asarray(ep['ports']['imu_J1']['pins'][pin])
        aa=np.asarray(ep['ports']['motion_J4']['axis']);ab=np.asarray(ep['ports']['imu_J1']['axis'])
        error=max(np.linalg.norm(points[0]-ea),np.linalg.norm(points[-1]-eb),
            np.linalg.norm(controls[0][0]-(ea+5*aa)),np.linalg.norm(controls[-1][-1]-(eb+5*ab)))
        max_endpoint_error=max(max_endpoint_error,float(error));checks['native_exits_and_straights']=error<.0001
        def unit(v):return v/np.linalg.norm(v)
        checks['terminal_tangents']=np.linalg.norm(unit(controls[0][1]-controls[0][0])-aa)<.0001 and np.linalg.norm(unit(controls[-1][-1]-controls[-1][-2])+ab)<.0001
        checks['middle_join']=all(np.linalg.norm(a[-1]-b[0])<.0001 and np.linalg.norm(unit(a[-1]-a[-2])-unit(b[1]-b[0]))<.0001 for a,b in zip(controls,controls[1:]))
        reconstructed=np.vstack([ea]+[bezier(c,np.linspace(0,1,181))[0 if k==0 else 1:] for k,c in enumerate(controls)]+[eb])
        error=float(np.max(np.linalg.norm(points-reconstructed,axis=1))) if len(points)==len(reconstructed) else float('inf')
        max_reconstruction_error=max(max_reconstruction_error,error);checks['stored_curve_matches_controls']=error<.0001
        r=min(extrema_radius(c)[0] for c in controls);minimum_radius=min(minimum_radius,r)
        checks['documented_radius']=r>=wire['required_radius_using_max_OD_mm']
        checks['recorded_radius']=abs(r-row['minimum_curvature_radius_mm'])<.0001
        checks['documented_OD']=abs(row['wire_OD_max_mm']-wire['insulation_OD_max_mm'])<1e-9
        checks['pin_identity']=row['pin']==int(pin) and row['from_port']=='motion_J4' and row['to_port']=='imu_J1'
        bad=[k for k,v in checks.items() if not v]
        if bad:failures.append(dict(candidate=i,failed=bad))
    rows.append(dict(pin=pin,candidates=len(pool),status='PASS' if not failures else 'FAIL',failures=failures,
        minimum_recomputed_radius_mm=minimum_radius,max_endpoint_error_mm=max_endpoint_error,
        max_curve_reconstruction_error_mm=max_reconstruction_error))
out=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',source_blend_sha256=source_hash,
    sources={str(p.relative_to(project)):sha(p) for p in [pool_file,ep_file,wire_file,root/'imu_individual_routes.py']},
    rows=rows,elapsed_s=time.time()-start,main_modified=False,
    scope='Native numbered assumed exits, five-millimetre straights, tangent continuity, polynomial curvature and stored curve identity',
    limits=['Endpoint plane/transverse wire exit and 5mm straight remain assumptions from the nominal mating housing.',
        'Alpha6711 is an unselected catalogue candidate; this audit does not qualify crimping, flexible motion, slack or manufacturing.'])
(root/'imu_axial_curve_datums.json').write_text(json.dumps(out,indent=2)+'\n')
print('AXIAL_CURVE_DATUMS',out['status'],sum(r['candidates'] for r in rows),'curves',out['elapsed_s'])
