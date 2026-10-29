"""Verify native via retention and power-anchor accounting on rejected R171 trials.

Positive and negative reviews use actual saved native boards. No failed retained
pad/power connection becomes a pass when an obsolete anchor is accounted for.
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from review_planned_delta import review
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');name='MORI_Interface_C3.kicad_pcb'
out=b/'R171-native-review';out.mkdir(exist_ok=False)
a=Copper(str(dev/'native'/name));original={uid(v):via_snapshot(a.board,v) for v in a.vias};retired='aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57';rows=[]
for rev in ['R171B','R171C','R171D','R171E']:
 c=Copper(str(b/rev/name));new={uid(v):via_snapshot(c.board,v) for v in c.vias}
 assert set(original)-set(new)=={retired} and len(set(new)-set(original))==1
 assert all(new[u]==s for u,s in original.items() if u!=retired)
 assert all(u in new and new[u]==s for u,s in original.items() if s['net']=='GND')
 rows.append(dict(revision=rev,board_sha256=c.sha,source_vias=len(original),source_ground_vias=sum(s['net']=='GND' for s in original.values()),exact_retained_source_vias=len(original)-1,removed_non_ground_via=retired,added_vias=1,status='PASS'))
r=review(str(dev/'native'/name),str(b/'R171E'/name),str(b/'R171E-plan.json'),str(b/'R171E-verify/regression.json'),str(dev/'evidence/R168G/regression.json'))
(out/'R171E-planned-delta.json').write_text(json.dumps(r,indent=2)+'\n')
assert r['status']=='FAIL' and set(r['errors'])=={'all_prior_pad_connections','power_width'},r['errors']
assert sum(x['status']=='FAIL' for x in r['power_width_review'])==3
assert sum(bool(x['removed_anchor_pairs']) for x in r['power_width_review'])==5
p=json.loads((b/'R171E-plan.json').read_text());p['remove_obsolete_vias'][0]['isolated_zone_layers']=['In3.Cu']
bad=out/'invalid_distributed_layer-plan.json';bad.write_text(json.dumps(p,indent=2)+'\n')
q=review(str(dev/'native'/name),str(b/'R171E'/name),str(bad),str(b/'R171E-verify/regression.json'),str(dev/'evidence/R168G/regression.json'))
(out/'invalid_distributed_layer-review.json').write_text(json.dumps(q,indent=2)+'\n')
assert q['status']=='FAIL' and 'obsolete_via_removed_'+retired in q['errors']
assert sum(x['status']=='FAIL' for x in q['power_width_review'])==7
assert all(not x['removed_anchor_pairs'] for x in q['power_width_review'])
assert hashlib.sha256((dev/'native'/name).read_bytes()).hexdigest()==a.sha
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=a.sha,via_checks=rows,valid_plan_review=dict(status=r['status'],checks=len(r['checks']),errors=r['errors'],retained_power_failures=3),invalid_plan_review=dict(status=q['status'],errors=q['errors'],retained_power_failures=7,removed_anchor_exclusions=0),status='PASS',adopted=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',candidate_checks=len(r['checks']),candidate_errors=r['errors'],invalid_plan_refused=True)),flush=True)
