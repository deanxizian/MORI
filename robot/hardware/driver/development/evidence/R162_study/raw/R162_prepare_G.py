"""Give the retained FAULT group a shorter bottom transfer near U1501.
This replaces E/D's long B-tail proposal by a separate exact native candidate
based on C. Both FAULT groups still await their inter-layer connection.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R162G-plan.json';assert not out.exists()
p=json.loads((b/'R162C-plan.json').read_text());p['revision']='R162G';p['scope']+='\n'+__doc__
p['vias'].append({'net':'/FAULT_N','position_mm':[54.3,33.9],'diameter_mm':.5,'drill_mm':.3})
p['routes'].append({'net':'/FAULT_N','layer':'B.Cu','width_mm':.2,'points_mm':[[54.3,33.9],[54.05,34.15],[53.4,34.15]]})
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
