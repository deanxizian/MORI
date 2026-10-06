"""Recheck saved connector paths and test extra physical-obstacle margins."""
from pathlib import Path
VERIFY_SCRIPT=Path(__file__).resolve();VERIFY_HELPER=VERIFY_SCRIPT.parent/'plan_CAM_later_ports_grid.py'
prefix=VERIFY_HELPER.read_text().split('\nrows=[]\noverall_started=',1)[0]
__file__=str(VERIFY_HELPER);exec(compile(prefix,str(VERIFY_HELPER),'exec'),globals());__file__=str(VERIFY_SCRIPT)
from itertools import product
import sys
margin_mode='--margin' in sys.argv
producer=VERIFY_HELPER
if margin_mode:
    GRID_OUT=LATER_OUT/'grid_margin_approach'
    producer=VERIFY_SCRIPT.parent/'plan_CAM_later_ports_margin.py'
record=json.loads((GRID_OUT/'screen.json').read_text())
assert record['script_sha256']==sha(producer)
if margin_mode:assert record['optimizer_base_sha256']==sha(VERIFY_HELPER)
assert record['helper_sha256']==sha(GRID_HELPER)
assert all(sha(PROJECT/p)==h for p,h in record['protected_sources'].items())
rows=[];started=time.time()
for row in record['rows']:
    port=row['port'];targets={n:d for n,d in base.items() if n!='Plug_'+port}
    m=plug[port].m;path=row['path_translations_mm'];segments=[]
    assert row['status']=='PASS' and path
    domain=m^phys[native_names[port.split('_')[0]]]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        swept=manifold.Manifold.batch_hull([m.translate(a),m.translate(b)])
        hit=collision_sweep(port,swept,targets,domain if i==0 else None)
        assert hit is None,(port,i,hit)
        margin_rows=[]
        if i>0:
            for pad in [.1,.2,.3]:
                padded=manifold.Manifold.batch_hull([swept.translate(list(c)) for c in product([-pad,pad],repeat=3)])
                bb=np.asarray(padded.bounding_box());fail=None
                for n,(solid,lo,hi,_) in targets.items():
                    if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):continue
                    volume=max(0.,float((padded^solid).volume()))
                    if volume>1e-5:
                        fail=dict(obstacle=n,padded_overlap_mm3=volume);break
                margin_rows.append(dict(clearance_mm=pad,status='PASS' if fail is None else 'BLOCKED',failure=fail))
        segments.append(dict(from_mm=a,to_mm=b,nominal_status='PASS',physical_margin_sweeps=margin_rows))
    rows.append(dict(port=port,status='PASS',segments=segments,
                     full_0_3_margin_status='PASS' if all(s['physical_margin_sweeps'][-1]['status']=='PASS' for s in segments[1:]) else 'BLOCKED'))
if margin_mode:assert all(r['full_0_3_margin_status']=='PASS' for r in rows)
report=dict(status='PASS',scope='Saved nominal convex sweeps replayed; extra physical clearance separately reported, initial mating not margin-qualified',
    script_sha256=sha(VERIFY_SCRIPT),helper_sha256=sha(VERIFY_HELPER),paths_sha256=sha(GRID_OUT/'screen.json'),
    margin_mode=margin_mode,producer_script_sha256=sha(producer),
    source_main_sha256=source_hash,protected_sources=protected,rows=rows,
    physical_margin_method='Convex sweep Minkowski-summed with an axis-aligned +/-margin cube; this contains a Euclidean margin ball',
    attached_wires='NOT_TESTED',hand_tools='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-started)
(GRID_OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LATER_PATH_VERIFY',[(r['port'],r['full_0_3_margin_status']) for r in rows],flush=True)
assert all(sha(PROJECT/p)==h for p,h in protected.items())
