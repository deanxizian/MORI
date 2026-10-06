from pathlib import Path
import sys,json,time,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sys.path.insert(0,str(HERE))
from curve_clearance import prepared,pair
from bounded_curve_checks import pair_threshold
pools=json.loads((OUT/'cam_lane_swap/body_prefix_screen.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f,h in {**pools['sources'],**pools['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(OUT/'cam_lane_swap/body_prefix_candidates.npz')==pools['curve_sha256']
meta=[x for a in pools['pools'].values() for x in a];data=np.load(OUT/'cam_lane_swap/body_prefix_candidates.npz')
key=lambda x:(x['lead_mm'],x['entry_deg'],x['exit_deg'],x['planar_radius_mm'],x['family'])
a={key(x):x for x in meta if x['pin']==1};b={key(x):x for x in meta if x['pin']==2}
items={x['id']:prepared(data[x['id']],x['OD_mm']/2,x['chord_error_mm']) for x in meta}
rows=[]
for k in set(a)&set(b):
 x,y=a[k]['id'],b[k]['id'];r=pair_threshold(items[x],items[y]);rows.append(dict(a=x,b=y,parameters=list(k),**r))
report=dict(status='PASS',scope='Paired-heading diagnosis only; no new combined route clearance approval',rows=rows,passes=sum(r['status']=='PASS' for r in rows),
 sources=pools['sources'],inputs={str(p.relative_to(ROOT)):sha(p) for p in
 [OUT/'cam_lane_swap/body_prefix_screen.json',OUT/'cam_lane_swap/body_prefix_candidates.npz',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']},
 script_sha256=sha(Path(__file__)),main_changed=False,full_harness='BLOCKED')
(OUT/'cam_same_heading_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print('SAME_HEADING',len(rows),report['passes'],flush=True)
