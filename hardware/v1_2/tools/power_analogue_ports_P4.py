"""Reserve two comparator input pin escapes before reconnecting neighbours."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import track,via,xy,F,B
from geometry_guard_P3R1 import Guard,obstacles
from route_local_P4 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_final_analogue_ports.kicad_pcb'),b)
remove={'2e8df2db-e664-4302-a474-00955d014943','c343e1b0-dfbc-4762-a82b-753f5ebff145','818d0268-6a27-4b65-984a-47b0bd2d4956'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove:b.Delete(t)
log=[]
for net,ps in [('/H_REF',[(60.525,39.635),(58.925,39.635)]),('/H_OVSENSE',[(65.475,38.365),(67.2,38.365)])]:
 g=Guard(b,net);a,z=ps
 if g.line_clear(a,z,B) and g.via_clear(z):
  track(b,net,ps,.2,B);via(b,net,*z,grid=False);log.append(dict(net=net,points=ps));print('escape added',net,flush=True)
 else:
  print('blocked escape',net,{str(l):obstacles(b,net,z,l,.8,True) for l in [F,B]},flush=True)
fps={f.GetReference():f for f in b.GetFootprints()}
def netpad(ref,net):return next(q for q in fps[ref].Pads() if q.GetNetname()==net)
a=xy(netpad('J3','/W9_IN').GetPosition());z=xy(netpad('D10','/W9_IN').GetPosition())
try:connect(b,'/W9_IN',a,z,[F,B],[B],(80,55),step=.05,width=1.5,vd=1,dr=.45,max_nodes=650000,time_limit=45)
except RuntimeError as e:print('W9_IN',e,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'final_analogue_ports.json').write_text(json.dumps(log,indent=2)+'\n')
