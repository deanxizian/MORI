"""Find the actual closest approach of cached rejected CAM3/4 combinations."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/entry_topology_review'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha,Vector
from curve_clearance import prepared,pair
ctx=Context();started=time.time();base=HERE/'remaining_routes'
report_file=base/'nine_four_order_expanded/combined/lower_nine_screen.json'
r=json.loads(report_file.read_text())
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
meta={};points={}
for name in ['nine_higher','cam_four_order','cam_four_order_expanded']:
    d=json.loads((base/name/'body_prefix_screen.json').read_text())
    for rows in d['pools'].values():meta.update({x['id']:x for x in rows})
    points.update(dict(np.load(base/name/'body_prefix_candidates.npz')))
items={k:prepared(p,.3302,meta[k]['chord_error_mm']) for k,p in points.items() if meta[k]['endpoint'] in ['CAM_3','CAM_4']}
checks=[]
for row in r['prefix_pair_checks']:
    a,b=row['a'],row['b']
    if a not in items or b not in items or meta[a]['endpoint']==meta[b]['endpoint']:continue
    result=pair(items[a],items[b]);p=result.get('point_mm')
    if p is not None:
        q,_,dist=items[b]['tree'].find(Vector(p));result['other_point_mm']=list(q)
    checks.append(dict(a=a,b=b,**result))
checks.sort(key=lambda r:r['gap_lower_bound_mm'],reverse=True)
best=checks[0];np.savez_compressed(OUT/'closest_cam34.npz',a=points[best['a']],b=points[best['b']])
ctx.assert_unchanged()
result=dict(status='PASS',scope='Global closest-approach diagnosis of previously rejected pairs, not a complete search or harness release',
    sources=ctx.sources,inputs={str(report_file.relative_to(ROOT)):sha(report_file)},
    count=len(checks),best_pairs=checks[:20],best_metadata={k:meta[best[k]] for k in ['a','b']},
    curves_sha256=sha(OUT/'closest_cam34.npz'),main_changed=False,full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'closest_cam34.json').write_text(json.dumps(result,indent=2)+'\n')
print('CAM34_DIAGNOSE_DONE',len(checks),best,time.time()-started,flush=True)
