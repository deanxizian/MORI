"""Joint placement study: free the front sampling corridor and reuse the existing UPS via.
No new drill, no ground-via move, no rule or plane edit. Native refill must verify
that relocating supply holes preserves all existing connectivity and copper width.
"""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
p=json.loads((b/'R158C-plan.json').read_text());p['revision']='R159A';p['scope']=__doc__
p['translations']=[s for s in p['translations'] if s['reference'] not in ['R1703','R1001']]
p['translations'] += [{'reference':'R1702','from_mm':[48,8.5],'delta_mm':[1.7,0]}, {'reference':'R1703','from_mm':[49.05,9.98],'delta_mm':[1.1,2.47]}]
p['move_vias'][0]['position_mm']=[47.3,8.6]
p['move_vias'][0]['reason']='Reuse the original UPS sampling via in the corridor freed by the front resistor pair, receiving power from existing UPS copper. Replace its old sampling escape and preserve every old UPS anchor through native refill; no bridge role is presumed.'
p['move_vias'][1]['position_mm']=[50.9,7.2]
p['move_vias'][1]['reason']='Relocate the original C505 feed hole beside its relocated capacitor and connect it explicitly on B.Cu; verify all former supply connections after refill. Do not rely on source fill overlap.'
p['vias']=[]
def delete(id_):
 if id_ in p['delete_copper']:return
 t=c.by_id[id_];p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for id_ in ['64b735e4-b7ed-451d-8dce-c8bc2f6a3f85','7e0606bf-69c9-4540-bf87-f2b7df14aefd','46b45438-08f9-40a3-97c0-eeccfd4d2b5b']:delete(id_)
# Replace the complete old front wheel tap, leaving its shunt landing in place.
for t in c.segments:
 if t.GetNetname()=='/WHEEL_VM' and t.GetLayer()==pcb.F_Cu:
  a,d=xy(t.GetStart()),xy(t.GetEnd())
  if min(a[0],d[0])>=47 and min(a[1],d[1])>=8.49 and max(a[1],d[1])<=12.56:delete(uid(t))
p['routes']=[r for r in p['routes'] if r['net'] not in ['/UPS_BAT','MOTION_3V3','Net-(R1702-~-Pad2)','Net-(U1702-INA+)'] and not (r['net']=='/WHEEL_VM' and r['layer']=='F.Cu')]
def route(n,l,w,points):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':points})
route('/UPS_BAT','B.Cu',.35,[[46.25,8.325],[46.25,8.6],[47.3,8.6]])
route('MOTION_3V3','B.Cu',.2,[[49.775,5.9],[52.25,5.9]])
route('MOTION_3V3','B.Cu',.2,[[50.9,5.9],[50.9,7.2]])
route('/WHEEL_VM','F.Cu',.2,[[48.875,8.5],[48.15,8.5],[48.15,12.55]])
route('Net-(R1702-~-Pad2)','F.Cu',.2,[[50.525,8.5],[50.525,8.8],[49.325,10],[49.325,12.45]])
route('Net-(U1702-INA+)','F.Cu',.2,[[50.975,12.45],[58.9375,12.45]])
# The former M5V hole caused the LIMIT reference-plane void. Move it only 0.15 mm
# upward and reconnect each native trace with the same width/layer/net.
id_='c9ef7bb5-bef9-48b7-b4cf-23501fe0a859';v=c.by_id[id_]
p['move_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,v),'position_mm':[44.5,10.1],'reason':'Test a 0.15 mm local shift of the existing 5 V via to restore the adjacent LIMIT reference corridor, with all its native copper explicitly reconnected; retain every ground via.'})
for t in c.segments:
 if t.GetNetname()!=v.GetNetname():continue
 a,d=list(xy(t.GetStart())),list(xy(t.GetEnd()))
 if a==[44.5,10.25] or d==[44.5,10.25]:
  delete(uid(t));a=[44.5,10.1] if a==[44.5,10.25] else a;d=[44.5,10.1] if d==[44.5,10.25] else d
  route(t.GetNetname(),c.board.GetLayerName(t.GetLayer()),t.GetWidth()/1e6,[a,d])
f=b/'R159A-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'plan':str(f),'deletions':len(p['delete_copper']),'routes':len(p['routes']),'moved_vias':len(p['move_vias']),'source_unchanged':c.sha}))
