"""Compare a top-side RLIMIT location with explicit B-face return to INA300 GND.

C505 moves above the group; only its non-ground 3V3 feed via and the UPS_BAT
sampling via move. All ground vias and U1701/input filters remain fixed. The
new RLIMIT ground trace terminates at the existing native GND8/bypass return,
not merely at the LATCH6 ground strap. No source rules or fills are changed.
Native refill and full regressions decide whether this study can be accepted.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
p={'revision':'R158A','board_sha256':c.sha,'scope':__doc__,'translations':[{'reference':'R1701','from_mm':[42.5,10.6],'delta_mm':[4.825,-.8],'rotation_deg':180},{'reference':'C505','from_mm':[49.1,9.8],'delta_mm':[-.1,-3.9]}],'delete_copper':[],'deleted_copper_expected':{},'move_vias':[],'routes':[],'vias':[],'adoption_prohibited_until_complete_verification':True}
for id_ in ['283e8a76-85a8-4770-9806-c99b814d086e','4b276614-22f2-4764-801a-f2163e40a1dc','adad3143-5df1-4ec5-880d-250d5d2e7fda','2676fa86-af16-488d-8e96-d09ab84abdbd','d782638a-9a73-4961-94f5-f6517808de6f','7fbd282c-71e5-45fd-b08b-e396095322e8','14c68f5c-96be-5ffa-8644-c62a6a64ab4b']:
 t=c.by_id[id_];p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for id_,pos in [('4150016a-d870-4d6e-beae-177f9b3cdd3a',[45.35,8.325]),('9fc6be27-25b2-4bce-8f44-98f39ccd1aa1',[47.3,6.2])]:p['move_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,c.by_id[id_]),'position_mm':pos})
def route(net,ly,w,pts):p['routes'].append({'net':net,'layer':ly,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','F.Cu',.5,[[45.35,11.655],[45.35,8.325]])
route('/UPS_BAT','B.Cu',.35,[[45.35,8.325],[46.25,8.325]])
route('MOTION_3V3','B.Cu',.2,[[48.225,5.9],[47.6,5.9],[47.3,6.2]])
route('GND','B.Cu',.2,[[49.775,5.9],[49.775,6.475],[49.15,7.1]])
route('Net-(U1701-LIMIT)','B.Cu',.2,[[46.5,9.8],[45.4,10.9],[44.025,10.9],[44.025,11.3]])
route('GND','B.Cu',.2,[[48.15,9.8],[49.43,9.8],[50.5,10.87]])
route('GND','B.Cu',.2,[[49.875,11.35],[49.875,10.245]])
route('/WHEEL_VM','B.Cu',.2,[[42.825,6.75],[42.825,7.2],[42.2,7.825],[42.2,10.95],[41.675,11.475],[41.675,12.15]])
f=b/'R158A-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R158A explicit plan created')
