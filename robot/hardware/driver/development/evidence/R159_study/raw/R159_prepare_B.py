"""Refine R159A with screened via locations and an explicit original-width UPS feed.
Trim and reroute the old comparator input trunk with full reference coverage;
this is an unaccepted study requiring native refill and complete regression.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R159A-plan.json').read_text());p['revision']='R159B';p['scope']=__doc__
p['translations'].append({'reference':'R1001','from_mm':[46.25,7.5],'delta_mm':[0,-.025]})
for v in p['move_vias']:
 if v['uuid']=='4150016a-d870-4d6e-beae-177f9b3cdd3a':v['position_mm']=[47.25,8.8];v['reason']='Move the existing UPS sampling via to the freed front corridor; retain explicit 0.50 mm F.Cu power feed plus 0.35 mm B.Cu sampling branch and verify original anchor widths after refill.'
 if v['uuid']=='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1':v['position_mm']=[50.9,6.5]
 if v['uuid']=='c9ef7bb5-bef9-48b7-b4cf-23501fe0a859':v['position_mm']=[44.575,10.1];v['reason']='Screened local shift clears the Q1601 land while opening the LIMIT reference corridor; reconnect original B.Cu feed at its full 0.40 mm width and recheck every old reference path.'
def delete(id_):
 if id_ in p['delete_copper']:return
 t=c.by_id[id_];p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
delete('5a53c1d0-b37f-5e34-ad95-cf4ddfe92ff7')
p['routes']=[r for r in p['routes'] if r['net'] not in ['/UPS_BAT','Net-(U1702-INA+)','/01 {slash} Core/MOTION_5V'] and not (r['net']=='MOTION_3V3' and r['points_mm'][0]==[50.9,5.9])]
def route(n,l,w,points):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':points})
route('/UPS_BAT','F.Cu',.5,[[43.8,12.155],[44.6,12.155],[45.5,11.255],[45.5,10.3],[47.25,10.3],[47.25,8.8]])
route('/UPS_BAT','B.Cu',.35,[[46.25,8.3],[46.25,8.8],[47.25,8.8]])
route('MOTION_3V3','B.Cu',.2,[[50.9,5.9],[50.9,6.5]])
route('/01 {slash} Core/MOTION_5V','B.Cu',.4,[[44.5,6.4],[44.575,10.1]])
route('Net-(U1702-INA+)','F.Cu',.2,[[50.975,12.45],[51.3,12.45],[51.6,12.75],[58.9375,12.75]])
route('Net-(U1702-INA+)','F.Cu',.2,[[58.9375,12.575],[58.9375,14.7]])
f=b/'R159B-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R159B plan written')
