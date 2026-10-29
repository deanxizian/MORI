"""Restore the original UPS plane transfer alongside a separate relocated sampling hole.
Retain the C505 via near its original wide local 3V3 component and explicitly
join it to the existing EN via on F.Cu; no source width exception is introduced.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R159B-plan.json').read_text());p['revision']='R159C';p['scope']=__doc__
for v in p['move_vias']:
 if v['uuid']=='4150016a-d870-4d6e-beae-177f9b3cdd3a':v['position_mm']=[45.3,10.125];v['reason']='Retain the original UPS F-to-In2 power transfer close to its old location. A separate sampling via occupies the freed front corridor; verify original supply anchors and reference copper after refill.'
 if v['uuid']=='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1':v['position_mm']=[46.875,10.725];v['reason']='Keep the original C505 feed via in its original local 3V3 power region, with a new short F.Cu connection to the existing EN feed via, preserving old width relationships and all ground vias.'
 if v['uuid']=='c9ef7bb5-bef9-48b7-b4cf-23501fe0a859':v['position_mm']=[44.575,10.125]
p['vias']=[{'net':'/UPS_BAT','position_mm':[47.25,8.8],'diameter_mm':.5,'drill_mm':.3}]
p['routes']=[r for r in p['routes'] if not (r['net']=='/UPS_BAT' and r['layer']=='F.Cu') and r['net'] not in ['Net-(U1701-LIMIT)','/01 {slash} Core/MOTION_5V'] and not (r['net']=='MOTION_3V3' and r['points_mm'][0]==[50.9,5.9])]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','F.Cu',.5,[[43.8,12.155],[44.85,12.155],[45.35,11.655],[45.35,10.175],[45.3,10.125]])
route('/UPS_BAT','F.Cu',.35,[[45.3,10.125],[46.1,10.125],[47.25,8.975],[47.25,8.8]])
route('MOTION_3V3','F.Cu',.2,[[46.875,10.725],[46.875,11.285],[46.3,11.86],[46.3,11.85]])
route('/01 {slash} Core/MOTION_5V','B.Cu',.4,[[44.5,6.4],[44.575,10.125]])
route('Net-(U1701-LIMIT)','B.Cu',.2,[[46.45,9.7],[46.45,10.08],[45.63,10.9],[44.025,10.9],[44.025,11.3]])
f=b/'R159C-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R159C plan written')
