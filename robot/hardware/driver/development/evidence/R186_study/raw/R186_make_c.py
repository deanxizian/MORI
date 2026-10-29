"""Improve the prep pair bends and retain the fixed comparator branch.

R1703's removed terminal walk included a junction shared by R1704 and U1702.
That fixed-to-fixed segment is retained here; all moved terminals still require
restoration. No source rule, outline, pin mapping or electrical value changes.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R186C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/'R186B-plan.json').read_text());assert plan['board_sha256']==c.sha
plan.update(revision='R186C',scope=__doc__)
chosen=[json.loads((b/('R186-'+g+'-smooth-pairs.json')).read_text())[0] for g in ['R1702_R1703','R1102_C1102']]
for group,pair in zip([('R1702','R1703'),('R1102','C1102')],chosen):
    for ref,key in zip(group,['first','last']):
        row=next(r for r in plan['translations'] if r['reference']==ref)
        row.update(delta_mm=pair[key]['delta_mm'],rotation_deg=pair[key]['rotation_deg'])
plan['routes']=[dict(net=p['net'],layer='F.Cu',width_mm=.2,points_mm=p['points_mm']) for p in chosen]
branch='c6322a91-08ee-5998-bebe-d80c60939e6c'
t=c.by_id[branch]
assert t.GetNetname()=='Net-(U1702-INA+)'
assert set([xy(t.GetStart()),xy(t.GetEnd())])=={(60.9,12.575),(58.9375,12.575)}
plan['delete_copper'].remove(branch);del plan['deleted_copper_expected'][branch]
out.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(preparation_only=True,retained_fixed_branch=branch,translations=plan['translations'],routes=plan['routes'])))
