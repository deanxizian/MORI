"""Identify old CAM body routes that conflict with the new five-line proposal."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from curve_clearance import prepared,pair
OUT=HERE/'remaining_routes';base=OUT/'five_before_cam_reroute'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((base/'lower_five_screen.json').read_text());assert report['status']=='PASS'
new=np.load(base/'lower_five_candidates.npz');old=np.load(HERE/'front_lower_curves.npz')
assert sha(base/'lower_five_candidates.npz')==report['curve_sha256']
five={r['endpoint']:prepared(new[r['endpoint']+'_y0'],.5842,max(r['chord_error_mm'],.00001)) for r in report['selected']}
cams={i:prepared(old[f'pin{i}_y0'],.3302,.0004) for i in range(1,5)}
rows=[dict(endpoint=k,CAM_pin=i,**pair(a,b)) for k,a in five.items() for i,b in cams.items()]
result=dict(status='BLOCKED' if any(r['status']!='PASS' for r in rows) else 'PASS',
    scope='Zero-pose diagnostic only, not whole routing or a waiver of old CAM material',rows=rows,
    CAM_pins_requiring_body_reroute=sorted({r['CAM_pin'] for r in rows if r['status']!='PASS'}),
    sources={str(p.relative_to(HERE)):sha(p) for p in [base/'lower_five_screen.json',base/'lower_five_candidates.npz',HERE/'front_lower_curves.npz']},
    script_sha256=sha(Path(__file__)),main_changed=False,full_harness='BLOCKED')
(OUT/'cam_body_conflicts.json').write_text(json.dumps(result,indent=2)+'\n')
print('CAM_BODY_REROUTE',result['CAM_pins_requiring_body_reroute'],flush=True)
