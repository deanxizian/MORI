"""All-pair sampled-curve distance bounds for the higher-entry local candidate."""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import np,sha
from common import P
from mathutils.kdtree import KDTree
from mathutils import Vector
start=time.time()
report=json.loads((HERE/'balanced_entry_screen.json').read_text())
assert report['status']=='PASS'
for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
file=HERE/'balanced_entry_candidates.npz';data=np.load(file)
assert sha(file)==report['curve_file_sha256']
OD=[s['OD_mm'] for s in P['neck_harness_capacity']['wire_allocations']]
chord=report['results'][0]['max_chord_error_mm'];rows=[]
for yaw in range(-60,61,10):
    curves=[data[f'case0_wire{i}_y{yaw}'] for i in range(11)]
    trees=[]
    for p in curves:
        tree=KDTree(len(p))
        for k,q in enumerate(p):tree.insert(Vector(q),k)
        tree.balance();trees.append(tree)
    steps=[np.linalg.norm(np.diff(p,axis=0),axis=1).max() for p in curves]
    for i in range(11):
        for j in range(i+1,11):
            d,k=min((float(trees[j].find(Vector(p))[2]),k) for k,p in enumerate(curves[i]))
            lower=d-(OD[i]+OD[j])/2-(steps[i]+steps[j])/2-2*chord-1e-4
            rows.append(dict(a=i,b=j,yaw=yaw,sample_distance_mm=d,gap_lower_bound_mm=lower,point_mm=curves[i][k].tolist(),status='PASS' if lower>=.3 else 'BLOCKED'))
minimum=min(rows,key=lambda r:r['gap_lower_bound_mm'])
result=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',scope='Local11-wire curve-pair clearance at13 sampled yaw poses, conservatively bounded between longitudinal samples; full endpoint routing and wired assembly incomplete',curve_sha256=sha(file),input_report_sha256=sha(HERE/'balanced_entry_screen.json'),sources=report['sources'],minimum=minimum,rows=rows,required_surface_gap_mm=.3,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start,full_harness='BLOCKED')
(HERE/'local_packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('LOCAL_PACKING',result['status'],minimum,flush=True)
