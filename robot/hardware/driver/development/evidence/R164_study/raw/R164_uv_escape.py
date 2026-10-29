"""Open a left-side UV output escape using an original upper transfer site.
The old direct ground trace is removed only in this independent trial; native
refill must prove the actual ground-pad/plane path remains. The UV input escape
is shortened so it does not cross the output channel. No ground via moves.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R164A-plan.json').read_text());p.update(revision='R164B',scope=__doc__)
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
uv='Net-(U1301-INA+_{slash}_UV)';outnet='/13 {slash} Head_Fault_Delay/HEAD_UV_N'
routes=[]
for r in p['routes']:
 if r['net']=='GND' and r['points_mm'][0]==[64.0625,27.9]:continue
 if r['net']==uv and r['layer']=='B.Cu' and r['points_mm'][0] in [[64.2,26.1],[63.4,26.525]]:continue
 if r['net']==outnet and r['layer']=='B.Cu':
  assert r['points_mm'][0]==[64.0625,28.85]
  r['points_mm']=[[64.0625,28.85],[63.075,28.85],[63.075,26.4],[62.75,26.075],[62.75,25.25]]
 routes.append(r)
routes.append({'net':uv,'layer':'B.Cu','width_mm':.2,'points_mm':[[64.2,26.1],[64.0625,26.2375],[64.0625,26.95]]})
p['routes']=routes
p['vias']=[v for v in p['vias'] if not (v['net']==outnet and v['position_mm']==[64.2,29.7])]
id_='b7a4befe-1ae6-40bc-a958-e0a34a8c803c';assert any(s['uuid']==id_ for s in p['remove_obsolete_vias'])
p['remove_obsolete_vias']=[s for s in p['remove_obsolete_vias'] if s['uuid']!=id_]
p['reassign_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,c.by_id[id_]),'net':outnet,
 'reason':'Reuse the original upper transfer opening for the relocated comparator output, without changing any native keepout or hole size. Old UV input is already restored by the explicit local chain.'})
p['ground_return_requires_native_fill_and_manufacturer_review']=True
path=b/'R164B-plan.json';assert not path.exists();path.write_text(json.dumps(p,indent=2)+'\n')
