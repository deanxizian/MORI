"""R160 joint packing proposal; unfinished native diagnostic, never adoption.

Uses the first scored compatible placement from the saved source-GND-aware
packing search. Copper is deliberately retained to identify exact replacement
scope. Native DRC and source ground-net identity must be inspected afterward.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
out=b/'R160B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
packing=json.loads((b/'R160-joint-packing.json').read_text())
assert c.sha==packing['source_sha256']=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
fps={f.GetReference():f for f in c.footprints}
poses=[dict(reference='U1301',**packing['fixed_U1301'])]+packing['solutions'][0]['poses']
translations=[]
for row in poses:
 ref=row['reference'];f=fps[ref];old=xy(f.GetPosition());pos=row['position_mm']
 spec={'reference':ref,'from_mm':list(old),'delta_mm':[round(pos[i]-old[i],6) for i in range(2)],'rotation_deg':row['rotation_deg']}
 if ref=='U1301':spec['reconstruct_fixed_via_guards']=True
 translations.append(spec)
plan={'revision':'R160B','board_sha256':c.sha,'scope':__doc__,'translations':translations,
      'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[],
      'adoption_prohibited_until_complete_verification':True,'diagnostic_only':True,
      'placement_evidence':'R160-joint-packing.json','placement_solution_index':0}
out.write_text(json.dumps(plan,indent=2)+'\n')
print('R160B source-GND-aware joint placement diagnostic recorded')
