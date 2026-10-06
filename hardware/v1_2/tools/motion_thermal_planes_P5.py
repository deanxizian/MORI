"""Use the dedicated ground plane for five crowded header ground pads.

Outer copper pours pull back; the pads retain four-spoke relief to In1.Cu.
No DRC severities, exclusions or source rule values are changed.
"""
import json,math
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_header_thermal_plan.kicad_pcb'),b)
f=next(f for f in b.GetFootprints()if f.GetReference()=='U100');log=[]
for q in f.Pads():
 if q.GetNumber() not in ['C2','C4','C6','D5','D6']:continue
 x,y=xy(q.GetPosition())
 for l in [F,B]:
  z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(l);z.SetZoneName('P5_HEADER_PLANE_'+q.GetNumber()+'_'+str(l));z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(True);o=z.Outline();o.NewOutline()
  for i in range(64):o.Append(mm(x+1.5*math.cos(i*math.pi/32)),mm(y+1.5*math.sin(i*math.pi/32)))
  b.Add(z)
 log.append(dict(ref='U100',pin=q.GetNumber(),net=q.GetNetname(),outer_pour_pullback_radius=1.5,connection_layer='In1.Cu',thermal_spokes=4))
# Move the DRDY via out of the 3V3 header pad's diagonal thermal corridor.
v=next(t for t in b.GetTracks()if t.m_Uuid.AsString()=='0f525362-ceab-485f-a961-d9d4d8ad01cc');old=xy(v.GetPosition());net=v.GetNetname();ends=[]
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA) or t.GetNetname()!=net:continue
 a,z=xy(t.GetStart()),xy(t.GetEnd())
 if min(math.dist(a,old),math.dist(z,old))<.41:ends.append((t,a,z,math.dist(a,old)<math.dist(z,old)))
b.Remove(v)
for t,*_ in ends:b.Remove(t)
g=Guard(b,net);chosen=None
for new in [(36.169599,30.7),(35.6,31.0),(35.56,30.8),(36.169599,30.5),(35.3,31.394399)]:
 if not g.via_clear(new):continue
 if all(g.line_clear(z if start else a,new,t.GetLayer(),k.ToMM(t.GetWidth()))for t,a,z,start in ends):chosen=new;break
for t,a,z,start in ends:
 if chosen:(t.SetStart if start else t.SetEnd)(pt(*chosen))
 b.Add(t)
if chosen:v.SetPosition(pt(*chosen))
b.Add(v);print('via',old,'->',chosen,flush=True)
k.SaveBoard(str(p),b);(r/'header_thermal_plan.json').write_text(json.dumps(dict(pads=log,signal_via_move=dict(net=net,old=old,new=chosen),reason='Dedicated In1 GND connection, avoid incomplete additional outer thermal connections; preserve source R25 four-spoke connections on the selected plane.'),indent=2)+'\n')
