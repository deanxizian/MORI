"""Refine the outside-corridor sampling supply and restore full nearby reference copper.
A northward UPS allocation connection avoids the fixed ground hole at (53.1,6.6).
Move the existing S2 via/its two surface segments upward 0.15 mm; replace its
inner segment with one deliberate straight run, preserving both endpoint nets.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R159D-plan.json').read_text());p['revision']='R159E';p['scope']=__doc__
for f in p['translations']:
 if f['reference']=='R1702':f['delta_mm']=[1.7,-.05]
 if f['reference']=='R1703':f['delta_mm']=[.65,-.055]
p['vias'][0]['position_mm']=[51.35,6.675]
z=p['power_zone_expansions'][0];z['union_patch_mm']=[[51.1,5.35],[53.1,5.35],[53.1,7.15],[51.1,7.15]];z['expected_added_area_mm2']=3.42;z['reason']='Connect the sampling via outside the received CAM 5 V corridor to the UPS allocation north of the fixed ground hole at (53.1,6.6). Preserve all original zone settings and compare all retained supply widths and reference paths after native refill.'
id_='3da8b3e2-7d4b-4ebe-87e6-877930d5d3f3';v=c.by_id[id_]
p['move_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,v),'position_mm':[45.6,9.2],'reason':'Shorten the local front S2 escape and lift the inner sense endpoint 0.15 mm away from the adjacent power-via ground-fill notch. Preserve the original net and dimensions, reconnect every original incident segment at its original width, and recheck all old reference paths.'})
def delete(id_):
 if id_ in p['delete_copper']:return
 t=c.by_id[id_];p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for id_ in ['cc6103ad-8528-4530-bbd6-8c16d5c66ab0','e4b67b22-d32a-459b-8b55-989fcafd816c','0b8273de-6a89-40ae-859d-fb125a9e5a56']:delete(id_)
p['routes']=[r for r in p['routes'] if r['net'] not in ['Net-(R1702-~-Pad2)','Net-(U1702-INA+)'] and not (r['net']=='/WHEEL_VM' and r['layer']=='F.Cu') and not (r['net']=='/UPS_BAT' and r['layer']=='B.Cu')]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/WHEEL_VM','F.Cu',.2,[[48.875,8.45],[48.15,8.45],[48.15,12.55]])
route('Net-(R1702-~-Pad2)','F.Cu',.2,[[50.525,8.45],[50.525,9.925]])
route('Net-(U1702-INA+)','F.Cu',.2,[[48.875,9.925],[48.6,9.925],[48.6,11.175],[49.875,12.45]])
route('/UPS_BAT','B.Cu',.35,[[46.25,8.3],[46.25,8.55],[50.85,8.55],[51.35,8.05],[51.35,6.675]])
route('Net-(U1001-S2_{slash}_WHEEL_sense)','F.Cu',.2,[[44.6,7.5],[44.6,9.2],[45.6,9.2]])
route('Net-(U1001-S2_{slash}_WHEEL_sense)','In3.Cu',.2,[[36.85,9.35],[45.6,9.2]])
f=b/'R159E-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R159E plan written')
