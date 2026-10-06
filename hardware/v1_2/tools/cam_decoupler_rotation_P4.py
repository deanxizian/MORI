"""Compare C7 orientations to give its ground pin a short plane connection.

Every accepted trial must reduce native opens without increasing hard errors.
No changes to the capacitor value, supply net, or logical connectivity.
"""
import sys,json,math,subprocess
import pcbnew as k
from helpers_P4 import paths
from layout_P3R1 import setplace,track,via,xy,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
from route_local_P4 import connect
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));backup=r/'before_C7_rotation.kicad_pcb';k.SaveBoard(str(backup),b)
base=json.loads((r/'drc.json').read_text());soft={'track_angle','track_dangling','via_dangling','track_not_centered_on_via','silk_over_copper','silk_overlap','starved_thermal'}
log=[];ok=False
for angle in [0,90,270]:
 b=k.LoadBoard(str(backup));f=next(f for f in b.GetFootprints() if f.GetReference()=='C7');oldpads=list(f.Pads())
 for t in list(b.GetTracks()):
  if t.Type()!=k.PCB_VIA_T and t.GetLayer()==B and any(t.GetNetname()==q.GetNetname() and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),0) for q in oldpads):b.Delete(t)
 setplace(f,37.5,14,angle,'B');create(b)
 gp=next(q for q in f.Pads() if q.GetNetname()=='/GND');cp=next(q for q in f.Pads() if q.GetNetname()=='/CAM_3V3');g=Guard(b,'/GND')
 port=next(g.portals(xy(gp.GetPosition()),B,radius=3,step=.1),None)
 if not port:log.append(dict(angle=angle,status='NO_GROUND_PORT'));continue
 _,pos,ps=port;track(b,'/GND',ps,.2,B);via(b,'/GND',*pos,grid=False)
 ends=[]
 for t in b.GetTracks():
  if t.GetNetname()=='/CAM_3V3':
   layers=[l for l in [F,B] if t.IsOnLayer(l)]
   ends.extend((math.dist(xy(cp.GetPosition()),v),v,layers) for v in [xy(t.GetStart()),xy(t.GetEnd())])
 routed=False
 for _,z,zl in sorted(ends)[:5]:
  try:connect(b,'/CAM_3V3',xy(cp.GetPosition()),z,[B],zl,(70,35),step=.05,width=.2,vd=.8,dr=.3,max_nodes=250000,time_limit=15);routed=True;break
  except RuntimeError:pass
 if not routed:log.append(dict(angle=angle,status='NO_CAM_ROUTE'));continue
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 cmd=['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/f'C7_{angle}_drc.json'),str(p)]
 subprocess.run(cmd,capture_output=True,check=True);j=json.loads((r/f'C7_{angle}_drc.json').read_text());hard=[v['type'] for v in j['violations'] if v['type'] not in soft]
 row=dict(angle=angle,ground_via_mm=pos,hard=hard,opens=len(j['unconnected_items']),argv=cmd);log.append(row);print(row,flush=True)
 if not hard and len(j['unconnected_items'])<len(base['unconnected_items']):ok=True;break
if not ok:p.write_bytes(backup.read_bytes())
(r/'C7_orientation_trials.json').write_text(json.dumps(dict(accepted=ok,trials=log),indent=2)+'\n')
