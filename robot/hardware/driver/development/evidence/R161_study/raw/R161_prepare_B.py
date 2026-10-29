"""Native geometry witness for the corrected nine-part group.
Preserves old copper intentionally to identify exact replacement work.
Not a routed candidate; never adopt this witness.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161B-plan.json';assert not out.exists()
g=json.loads((b/'R161-Bgroup.json').read_text());assert all(not r['hard_clashes'] for r in g['placements'])
import sys
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==g['source_sha256']
fs={f.GetReference():f for f in c.footprints};tr=[]
for row in g['placements']:
 ref=row['reference'];old=list(xy(fs[ref].GetPosition()));pos=row['position_mm']
 spec={'reference':ref,'from_mm':old,'delta_mm':[round(pos[i]-old[i],6) for i in range(2)],'rotation_deg':row['rotation_deg']}
 if ref=='U1301':spec.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True)
 tr.append(spec)
p={'revision':'R161B','scope':__doc__,'board_sha256':c.sha,'translations':tr,'routes':[],'vias':[],
 'adoption_prohibited_until_complete_verification':True}
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R161B','translations':len(tr),'old_copper_preserved':True}))
