"""Bare-board mass scenarios; no claim of measured or populated-board mass."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent;H=O.parents[1]
h=json.loads((H/'handoff/mechanical_P4.json').read_text());out=[]
for name,b in h['boards'].items():
 a=b['outline_mm'][0]*b['outline_mm'][1]/100
 copper_cm=b['copper_nominal_um']*b['copper_layers']/10000
 core_cm=b['pcb_thickness_mm']/10-copper_cm
 estimates=[]
 for density,fill in [(1.85,.35),(1.95,.6),(2.05,.85)]:
  estimates.append(dict(FR4_density_g_cm3=density,copper_area_fraction=fill,mass_g=round(a*core_cm*density+a*copper_cm*8.96*fill,3)))
 out.append(dict(board=name,pcb_sha256=b['pcb_sha256'],area_cm2=a,copper_layers=b['copper_layers'],nominal_copper_per_layer_um=b['copper_nominal_um'],scenarios=estimates,populated_mass_g=None))
report=dict(status='NOT_TESTED',method='Native rectangular gross area, stated stack-up, three ASSUMED density/copper coverage scenarios; holes not subtracted; components/plugs/solder/wires excluded. Scenarios are not guaranteed min/max bounds.',boards=out,sum_bare_board_scenario_g=[round(sum(r['scenarios'][i]['mass_g'] for r in out),3) for i in range(3)],whole_robot_COM_inertia='BLOCKED: no measured populated mass and current mechanical mounting transforms not integrated')
(O/'bare_board_mass.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
