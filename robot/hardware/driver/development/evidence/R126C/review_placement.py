import sys,json,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
c=Copper('robot/.state/c3-completion/trials/R126C/MORI_Interface_C3.kicad_pcb');names={uid(p):c.pad_name(p) for p in c.pads};pn={n:i for i,n in names.items()};out={'board_sha256':c.sha,'drain_groups':c.pad_groups()['Net-(Q1401-D)'],'source_ground_corridor':[],'drain_width_corridor':[],'poses':{}}
for net,key,pin in [('Net-(Q1401-D)','drain_width_corridor','Q1401.3'),('GND','source_ground_corridor','Q1401.2')]:
 for w in [0,.2,.3,.4,.48]:
  pairs=c.connected_pairs(net,w);id_=pn[pin];others={b if a==id_ else a for a,b in pairs if id_ in (a,b)};out[key].append({'width_mm':w,'other_pad_count':sum(v in names for v in others),'resistor_pads':[names[v] for v in others if v in names and names[v].startswith('R141')],'ground_stitch_21_75_15_55_connected':'12f79216-6b20-476a-a590-f1c06d08fcb9' in others})
for ref in ['Q1401','R1406','R1407']:
 f=next(f for f in c.footprints if f.GetReference()==ref);out['poses'][ref]={'position_mm':xy(f.GetPosition()),'native_angle_deg':f.GetOrientationDegrees(),'pads':[{'pin':p.GetNumber(),'net':p.GetNetname(),'position_mm':xy(p.GetPosition())} for p in f.Pads()]}
q=next(p for p in c.pads if c.pad_name(p)=='Q1401.2');out['source_to_retained_ground_stitch_mm']=Point(xy(q.GetPosition())).distance(Point(21.75,15.55))
plan=json.loads(Path('robot/.state/c3-completion/trials/plan-R126C.json').read_text());out['route_lengths_mm']=[{'net':r['net'],'width_mm':r['width_mm'],'length_mm':LineString(r['points_mm']).length} for r in plan['routes']]
out['scope']='Geometric pad topology, width corridor and pose checks only; no current/pulse/thermal/EMC qualification.'
Path('robot/.state/c3-completion/trials/R126C-placement-review.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
