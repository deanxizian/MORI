"""Reserve solderable ground paths, then route control/sense lines around them."""
import pcbnew as k,json,math
from layout_P3 import paths,xy,pt,F,B,track,via
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_thermal_corridors.kicad_pcb'),b);fps={f.GetReference():f for f in b.GetFootprints()}
ids=['82f4c3c7-8e27-4b8c-b530-42e9b63b7895','4e3233d6-f249-429d-9160-2a4bad691b6e','7d331575-2eb9-4e92-abf5-59f65ba9884c','defd485a-55c6-43a8-9a7a-e49ba6c4d0c7','c411baef-a08f-4c08-a839-b79022633d35','c88d73a2-07b7-4742-8e84-08374cd7ffda','e6f96574-ef5d-4ffb-9172-4a7b62fcd48e','5c6c1cab-dda6-40af-a0d9-49f3b3b96f0c','161c9f49-4e26-4b04-b073-ab7f214750f7','4bad4781-f369-4830-8170-9f499e781e44','d4ab6626-328b-4ff3-8dc9-4a8f278809ec','a0606de4-bd8a-4ce5-b244-5b6b975a649f']
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/ARM_Q','/W_BRAKE_GATE','/M5_EN'] or t.m_Uuid.AsString() in ids or (isinstance(t,k.PCB_VIA) and t.GetNetname()=='/+5V_MOTION' and math.dist(xy(t.GetPosition()),(36.6802,18.2733))<.01):b.Delete(t)
points=[(41.3,25.7),(38.225,25.7),(38.225,23.905)];g=Guard(b,'/W_PRE');assert all(g.line_clear(a,z,B,1.5) for a,z in zip(points,points[1:]));track(b,'W_PRE',points,1.5,B)
log=[]
for ref,pn in [('JP60','2'),('J7','1')]:
 q=[q for q in fps[ref].Pads() if q.GetNumber()==pn][0];a=xy(q.GetPosition())
 for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  g=Guard(b,'/GND')
  for dd in [1.25+i*.1 for i in range(24)]:
   v=(round(a[0]+sx*dd,5),round(a[1]+sy*dd,5))
   if not g.via_clear(v):continue
   layers=[l for l in [F,B] if g.line_clear(a,v,l,.3)]
   if not layers:continue
   via(b,'GND',*v,grid=False)
   for l in layers:track(b,'GND',[a,v],.3,l)
   log.append(dict(ref=ref,corner=[sx,sy],via=v,layers=layers));break
  else:print('no corner via',ref,sx,sy,flush=True)
k.SaveBoard(str(p),b)
# All destinations are actual copper pins/branches, not inferred schematic coordinates.
def pad(ref,pn):return [q for q in fps[ref].Pads() if q.GetNumber()==str(pn)][0]
jobs=[('/BAT_MON',xy(pad('R50',1).GetPosition()),xy(pad('R4',1).GetPosition()),[B],[B]),('/+5V_MOTION',(36.6802,25.0448),(40,16.5),[F],[F]),('/M5_EN',xy(pad('U60',5).GetPosition()),xy(pad('JP60',1).GetPosition()),[F],[F,B])]
for net in ['/ARM_Q','/W_BRAKE_GATE']:
 pads=[q for f in fps.values() for q in f.Pads() if q.GetNetname()==net]
 pairs=[];connected=[pads.pop(0)]
 while pads:
  _,i,root=min((math.dist(xy(a.GetPosition()),xy(z.GetPosition())),i,z) for i,a in enumerate(pads) for z in connected)
  a=pads.pop(i);jobs.append((net,xy(a.GetPosition()),xy(root.GetPosition()),[l for l in [F,B] if a.IsOnLayer(l)],[l for l in [F,B] if root.IsOnLayer(l)]));connected.append(a)
for net,a,z,al,zl in jobs:
 try:log.append(connect(b,net,a,z,al,zl,(80,55),step=.05));k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True);log.append(dict(net=net,error=str(e)))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'thermal_corridors.json').write_text(json.dumps(log,indent=2)+'\n')
