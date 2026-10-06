"""Tighten conservative wire-pair bounds without changing curve geometry."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/cam_rearward_loops'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import np,sha
from curve_clearance import prepared,pair
from upper_pack_geometry import refined
started=time.time();d=json.loads((BASE/'loop_screen.json').read_text())
for name,h in {**d['sources'],**d['inputs']}.items():assert sha(ROOT/name)==h,name
assert sha(BASE/'curves.npz')==d['curve_sha256']
curves=np.load(BASE/'curves.npz');results=[]
for row in d['results']:
    if row.get('hits') or row.get('lower_conflicts') or len(row.get('self_checks',[]))!=40:continue
    assert row['native_checks']==600 and all(r['status']=='PASS' for r in row['self_checks'])
    case=row['id'];checks=[]
    for pitch in range(-20,26,5):
        items={p:prepared(refined(curves[f'{case}_pin{p}_pitch{pitch}']),.3302,.0003) for p in range(1,5)}
        for a,b in itertools.combinations(items,2):checks.append(dict(pitch=pitch,a=a,b=b,**pair(items[a],items[b])))
    passed=all(r['status']=='PASS' for r in checks)
    results.append(dict(id=case,status='PASS' if passed else 'BLOCKED',mutual=checks,
        reused_subchecks='600 current-solid checks,40 self checks,zero lower conflicts from hash-verified loop_screen.json; its original coarse pair failure remains preserved',
        minimum_gap_bound_mm=min(r['gap_lower_bound_mm'] for r in checks)))
    print('REARWARD_PAIRS',case,results[-1]['status'],results[-1]['minimum_gap_bound_mm'],flush=True)
inputs=[BASE/'loop_screen.json',BASE/'curves.npz',HERE/'curve_clearance.py',HERE/'upper_pack_geometry.py']
r=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',sources=d['sources'],inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    scope='Only current-solid/local-neck/loop-self/loop-mutual checks; no upper fan connection or full harness proof',results=results,
    maximum_refinement_step_mm=.01,source_curve_error_mm=.0003,required_gap_mm=.3,curves_changed=False,
    main_changed=False,full_harness='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(BASE/'refined_pairs.json').write_text(json.dumps(r,indent=2)+'\n')
print('REARWARD_PAIRS_DONE',r['status'],r['elapsed_s'],flush=True)
