"""Compare threshold exclusion against the full nearest-sample reference."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from curve_clearance import prepared,pair
from bounded_curve_checks import pair_threshold
OUT=HERE/'remaining_routes';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=OUT/'five_combination/lower_five_screen.json';r=json.loads(source.read_text())
files=[OUT/'thermothin2622/body_prefix_candidates.npz',OUT/'thermothin2622_r65/body_prefix_candidates.npz']
data=[np.load(f) for f in files];curves={}
for d in data:
    for k in d.files:
        if k.startswith('P_J18') and 'J18' in k:curves.setdefault(k,d[k])
        if k.startswith('P_J9_3'):curves[k]=d[k]
chosen=[]
for status in ['PASS','BLOCKED']:
    group=[x for x in r['body_pair_checks'] if x['status']==status]
    chosen.extend(group[i] for i in np.linspace(0,len(group)-1,50,dtype=int))
items={k:prepared(p,.5842,.0004) for k,p in curves.items()};rows=[];start=time.time()
for case in chosen:
    a,b=items[case['a']],items[case['b']]
    full=pair(a,b);threshold=pair_threshold(a,b)
    rows.append(dict(a=case['a'],b=case['b'],full=full,threshold=threshold,equivalent=full['status']==threshold['status']))
assert all(row['equivalent'] for row in rows)
report=dict(status='PASS',scope='100 real candidate pairs compared with unpruned global nearest-sample calculation; geometric algorithm check only',
    cases=rows,sources={p.name:sha(p) for p in files},input_report_sha256=sha(source),
    implementation_sha256=sha(HERE/'bounded_curve_checks.py'),reference_sha256=sha(HERE/'curve_clearance.py'),
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'curve_threshold_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('THRESHOLD_REFERENCE',report['status'],len(rows),flush=True)
