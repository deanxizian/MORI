"""Independent combined ADC/CLR proposal, not adopted.

Relocated R301 enables a short B-face D3 route. Common ADC uses a different
escape and the prospective (25.6,9.75) transfer. Move only an existing In3 CLR
corner around that via; preserve U701 BOOT/FB/capacitor source bytes. Native
refill and all old connection/power/reference regressions remain mandatory.
"""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper(b/'R139A/MORI_Interface_C3.kicad_pcb')
search=json.loads((b/'R139A-joint-search/searches.json').read_text())
adc='/01 {slash} Core/ACT_CURRENT_ADC';d3='Net-(U1001-D3_{slash}_current_ADC)'
plan={'revision':'R139B','board_sha256':c.sha,'scope':__doc__,'delete_copper':['5d3e402d-ab89-4466-b38e-c8771004d447','82c61ad3-bbb2-468a-a02f-57a2803d4731','c74cd486-ee0e-4fbb-97e7-6701087a2826'],'deleted_copper_expected':{},'routes':[],'vias':[]}
for u in plan['delete_copper']:
 t=c.by_id[u];plan['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
def add(net,layer,pts,width=.2):plan['routes'].append({'net':net,'layer':layer,'width_mm':width,'points_mm':pts})
r=next(x for x in search if x['net']==d3)['result'];assert r['status']=='PROPOSAL';plan['routes'] += [{'net':d3,**x} for x in r['routes']]
r=copy.deepcopy(json.loads((b/'R139A-via-reference-diagnostic/searches.json').read_text())[0]['result']);assert r['status']=='PROPOSAL'
for x in r['routes']:
 for pt in x['points_mm']:
  if pt==[25.8,9.75]:pt[0]=25.6
 # Maintain deliberate 45-degree entry to the shifted transfer.
 if x['layer']=='B.Cu' and x['points_mm'][-1]==[25.6,9.75]:x['points_mm'][-2]=[26.05,10.2]
 if x['layer']=='In3.Cu':x['points_mm'][1]=[25.6,12.25]
 plan['routes'].append({'net':adc,**x})
for v in r['vias']:
 if v['position_mm']==[25.8,9.75]:v['position_mm']=[25.6,9.75]
 plan['vias'].append({'net':adc,**v})
add(adc,'B.Cu',[[19.65,28.6],[20.275,28.6]])
add('/CLR_N','In3.Cu',[[24.76,9.61],[24.76,8.91],[25.46,8.21]])
add('/CLR_N','B.Cu',[[27.4,13.8],[28.05,14.45],[29.1,14.45],[29.55,14],[30.4,14]])
add('/CLR_N','B.Cu',[[24.76,9.61],[26.02,8.35],[26.65,8.35],[26.8,8.2],[26.8,7.5]])
r=next(x for x in search if x['net']=='/CLR_N' and 'J102.4' in x['groups'][0] and x['groups'][1]==['R301.1'])['result'];assert r['status']=='PROPOSAL'
plan['routes'] += [{'net':'/CLR_N',**x} for x in r['routes']]
plan['vias'] += [{'net':'/CLR_N',**v} for v in r['vias']]
p=b/'R139B-plan.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'routes':len(plan['routes']),'vias':len(plan['vias']),'deleted_tracks':len(plan['delete_copper'])}))
