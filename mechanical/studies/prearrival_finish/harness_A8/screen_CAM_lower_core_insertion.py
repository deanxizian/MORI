"""Reverse the service split: populate the head/upper shell on the bench.

The populated load frame and lower drive assembly enter from below. No part
is omitted to waive a collision; each of the 209 source members is assigned.
This checks rigid solids only; cables and real manipulation remain separate.
"""
from pathlib import Path
THIS=Path(__file__).resolve(); HELPER=THIS.parent/'screen_CAM_complete_head_insertion.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nheadsets=',1)[0],str(HELPER),'exec'),globals())
__file__=str(THIS)
LOWER=OUT/'lower_core';LOWER.mkdir(exist_ok=True)
started=time.time();rows=[]
headfixed=placed(upper|moving,I)
poses=[trans(z=-float(z)) for z in np.linspace(0,200,401)]
for label,ids in [('populated_core_and_drive',fixture)]:
    failure=None;checked=0
    for index,T in enumerate(poses):
        hits=pairs(placed(ids,T),headfixed);checked+=1
        if hits:failure=dict(index=index,offset_z_mm=float(T[2,3]),hits=hits);break
    row=dict(candidate=label,status='BLOCKED' if failure else 'PASS',checked_positions=checked,
        planned_positions=len(poses),failure=failure)
    rows.append(row);print('LOWER_CORE_INSERTION',row,flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite downward removal / upward insertion of complete lower core into prebuilt upper shell and head',
    script_sha256=sha(THIS),helper_sha256=sha(HELPER),source_main_sha256=source_hash,protected_sources=protected,
    fixed_members=sorted(upper|moving),moving_members=sorted(fixture),deferred_members=sorted(deferred),
    source_objects=len(ss),source_rigid_screen_sha256=sha(OUT/'rigid_screen.json'),rows=rows,
    path='Translate lower core -Z by 200 mm; reverse for installation',step_mm=.5,
    rigid_intersection_threshold_mm3=1e-5,full_wires='NOT_TESTED',continuous_motion='NOT_TESTED',
    upper_shell_bridge_bench_assembly='NOT_TESTED',bridge_bolt_tool_access='NOT_TESTED',
    no_universal_impossibility_claim=True,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-started)
(LOWER/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('LOWER_CORE_INSERTION_DONE',report['status'],round(time.time()-started,2),flush=True)
