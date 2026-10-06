"""Independently distinguish a true overlap from a margin-only rejection."""
from pathlib import Path
import json,hashlib
STAGE=Path(__file__).resolve().parent
code=(STAGE/'check_static.py').read_text().split('specs=[')[0]
exec(compile(code,str(STAGE/'check_static.py'),'exec'),globals())
data=json.loads((STAGE/'imu_slot_assembly_pools.json').read_text())
rows=[]
for search in data['search']:
    for hit in search['rejects'][:2]:
        p=np.asarray(hit['point_local_mm']);n=hit['object']
        loc,norm,face,d=trees[n].find_nearest(Vector(p))
        small=manifold.Manifold.sphere(.05,32).translate(p.tolist())
        tiny=max(0,(small^obstacles[n].m).volume())
        clearance=manifold.Manifold.sphere(.508+.3,32).translate(p.tolist())
        v=max(0,(clearance^obstacles[n].m).volume())
        row=dict(pin=search['pin'],**hit,nearest=list(loc),normal=list(norm),distance=float(d),
            signed_nearest_face_dot=float((Vector(p)-loc).dot(norm)),tiny_probe_intersection_mm3=tiny,
            nominal_wire_plus_margin_intersection_mm3=v)
        rows.append(row);print('FILTER_REJECTION_AUDIT',json.dumps(row),flush=True)
(STAGE/'deck_slot_review/filter_rejection_audit.json').write_text(json.dumps(dict(source_blend_sha256=source_hash,
    source_filter_sha256=hashlib.sha256((STAGE/'imu_slot_assembly_pools.json').read_bytes()).hexdigest(),rows=rows,
    main_modified=False),indent=2)+'\n')
