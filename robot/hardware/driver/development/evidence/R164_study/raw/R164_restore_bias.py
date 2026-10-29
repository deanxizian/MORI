"""Restore the bias pair through its original enable transfer/main branch.
Rebuild from R159H using the whole R163F plan. No source GND via, fixed
interface, circuit value, net, board outline or native rule is changed.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R163F-plan.json').read_text());p.update(revision='R164A',scope=__doc__)
preview=json.loads((b/'R164-bias-assignment-v2.json').read_text());assert preview['placement_conflict_count']==0
for spec in p['translations']:
 if spec['reference'] in ['R1311','R1312']:
  target=[68.8,18.25] if spec['reference']=='R1311' else [68.8,21.25]
  spec['delta_mm']=[round(a-z,6) for a,z in zip(target,spec['from_mm'])];spec['rotation_deg']=90
restored={'c327aae5-610d-4bfa-bac6-0b685880c8fb','e518cf78-8855-44fb-b1e4-749f134ebe36'}
assert restored<=set(p['delete_copper'])
p['delete_copper']=[u for u in p['delete_copper'] if u not in restored]
for u in restored:p['deleted_copper_expected'].pop(u)
via='61f593f6-35ac-484f-8d2f-a7902a0a6d0e';assert any(s['uuid']==via for s in p['remove_obsolete_vias'])
p['remove_obsolete_vias']=[s for s in p['remove_obsolete_vias'] if s['uuid']!=via]
for r in p['routes']:
 if r['net']=='Net-(R1311-~-Pad1)':r['points_mm']=[[68.8,19.075],[68.8,20.425]]
p['routes'] += [
 {'net':'/HEAD_UV_ENABLE','layer':'B.Cu','width_mm':.2,'points_mm':[[68.8,17.425],[68.8,16.875],[69.15,16.525]]},
 {'net':'GND','layer':'B.Cu','width_mm':.3,'points_mm':[[68.8,22.075],[68.8,23.475]]},
]
p['unfinished_connections']=['HEAD_UV_N original output','all canonical remaining nets']
out=b/'R164A-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':p['revision'],'restored_source_tracks':len(restored),'restored_source_enable_via':via}))
