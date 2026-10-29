"""Joint C1301/R1503 F-face placement and actual short UV filter connection.
Returns to the electrically preserved E working layout. The four mutually
incompatible raster proposals in F are not reused. No adoption is implied.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R161G-plan.json';assert not out.exists()
p=json.loads((b/'R161E-plan.json').read_text());p['revision']='R161G';p['scope']+='\n'+__doc__
r=next(r for r in p['translations'] if r['reference']=='C1301')
r['delta_mm']=[24.225,2.15];r['rotation_deg']=0
p['translations'].append({'reference':'R1503','from_mm':[65.75,28.0],'delta_mm':[3.15,.5],'rotation_deg':90})
p['routes'][12]['points_mm']=[[67.6,28.5],[67.2,28.1],[67.2,27.0],[67.4,26.8],[68.4,26.8],[68.9,27.3],[68.9,27.675]]
p['routes'][13]['points_mm']=[[68.9,29.325],[68.25,29.325],[68.0,29.075],[65.05,29.075],[65.0,29.95]]
net='Net-(U1301-INA+_{slash}_UV)'
p['vias'].append({'net':net,'position_mm':[64.2,26.1],'diameter_mm':.5,'drill_mm':.3})
p['routes'].extend([
 {'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[64.2,26.1],[63.775,26.525],[63.4,26.525]]},
 {'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[64.2,26.1],[64.2,27.225],[64.975,28.0]]},
])
p['unfinished_connections']=p['unfinished_connections'][:-1]
p['filter_path_requires_native_verification']=True
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
