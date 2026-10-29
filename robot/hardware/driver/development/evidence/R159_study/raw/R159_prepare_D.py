"""Joint native study with sampling via outside the CAM 5 V corridor.
Expand only the existing UPS In2 allocation by an exact 1.52 mm2 local patch.
The front series pair is aligned/rotated to preserve the original input trunk.
All ground vias, interfaces and design-rule settings remain fixed.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_snapshot
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R159C-plan.json').read_text());p['revision']='R159D';p['scope']=__doc__
for f in p['translations']:
 if f['reference']=='R1702':f['delta_mm']=[1.7,-.1]
 if f['reference']=='R1703':f['delta_mm']=[.65,-.08];f['rotation_deg']=180
for v in p['move_vias']:
 if v['uuid']=='4150016a-d870-4d6e-beae-177f9b3cdd3a':v['position_mm']=[45.29,10.125]
 if v['uuid']=='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1':v['position_mm']=[47.15,10.55]
p['vias']=[{'net':'/UPS_BAT','position_mm':[51.4,6.75],'diameter_mm':.5,'drill_mm':.3}]
# Keep the exact original long comparator trunk and its terminal vertical.
for id_ in ['46b45438-08f9-40a3-97c0-eeccfd4d2b5b','5a53c1d0-b37f-5e34-ad95-cf4ddfe92ff7']:
 p['delete_copper'].remove(id_);p['deleted_copper_expected'].pop(id_)
p['routes']=[r for r in p['routes'] if r['net'] not in ['/UPS_BAT','Net-(U1701-LIMIT)','Net-(U1702-INA+)','Net-(R1702-~-Pad2)'] and not (r['net'] in ['/WHEEL_VM','MOTION_3V3'] and r['layer']=='F.Cu')]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','F.Cu',.5,[[43.8,12.155],[44.6,12.155],[45.29,11.465],[45.29,10.125]])
route('/UPS_BAT','B.Cu',.35,[[46.25,8.3],[46.25,8.55],[50.85,8.55],[51.4,8.0],[51.4,6.75]])
route('MOTION_3V3','F.Cu',.2,[[47.15,10.55],[47.15,11.0],[46.3,11.85]])
route('Net-(U1701-LIMIT)','B.Cu',.2,[[46.45,9.7],[46.45,10.04],[45.59,10.9],[44.025,10.9],[44.025,11.3]])
route('/WHEEL_VM','F.Cu',.2,[[48.875,8.4],[48.15,8.4],[48.15,12.55]])
route('Net-(R1702-~-Pad2)','F.Cu',.2,[[50.525,8.4],[50.525,9.9]])
route('Net-(U1702-INA+)','F.Cu',.2,[[48.875,9.9],[48.6,9.9],[48.6,11.175],[49.875,12.45]])
z=next(z for z in c.zones if uid(z)=='eb787317-b097-455e-8de2-e8eefb9cb5a6')
p['power_zone_expansions']=[{'uuid':uid(z),'source_expected':zone_snapshot(c.board,z),'union_patch_mm':[[51.1,6.35],[53.1,6.35],[53.1,7.15],[51.1,7.15]],'expected_added_area_mm2':1.52,'reason':'Move the low-current R1001 input sampling via completely outside the received CAM UPS_5V corridor. The new 0.8 mm allocation neck joins the existing UPS power zone without changing its priority, fill, spacing or thermal rules; native refill and all old supply/reference checks must pass.'}]
f=b/'R159D-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'revision':'R159D','deletions':len(p['delete_copper']),'routes':len(p['routes']),'added_allocation_area_mm2':1.52}))
