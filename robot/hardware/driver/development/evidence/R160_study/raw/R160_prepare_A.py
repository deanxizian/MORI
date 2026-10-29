"""Joint placement-only prototype for the TPS3700 and its input filters/dividers.
This deliberately unfinished diagnostic retains old copper to expose all local
conflicts before rerouting. It is not a connectivity candidate and must not be
adopted. All fixed mechanical interfaces, original ground vias and native rules
remain present. No manufacturing or physical qualification is inferred.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R160A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
fps={f.GetReference():f for f in c.footprints}
poses={'U1301':((64.25,27.5),90),'C1303':((67.45,26.5),0),'R1307':((63.5,30.3),0),
       'R1502':((64.7,31.8),0),'R1303':((60.65,24.8),90),'C1302':((62.9,24.5),0),
       'C1301':((68.0,28.8),0)}
translations=[]
for ref,(pos,angle) in poses.items():
 f=fps[ref];old=xy(f.GetPosition());d={'reference':ref,'from_mm':list(old),'delta_mm':[round(pos[i]-old[i],6) for i in range(2)],'rotation_deg':angle}
 if ref=='U1301':d['reconstruct_fixed_via_guards']=True
 translations.append(d)
plan={'revision':'R160A','board_sha256':c.sha,'scope':__doc__,'translations':translations,
      'delete_copper':[],'deleted_copper_expected':{},'routes':[],'vias':[],
      'adoption_prohibited_until_complete_verification':True,'diagnostic_only':True}
out.write_text(json.dumps(plan,indent=2)+'\n');print('R160A joint placement-only plan recorded')
