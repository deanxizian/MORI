import pcbnew as k,json
from layout_P3 import paths,xy,pt,track,via,F,B
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
def q(ref,n):return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==str(n)).GetPosition())
for t in list(b.GetTracks()):
 a,z=xy(t.GetStart()),xy(t.GetEnd())
 if t.GetNetname() in ['/W_DUMP_D','/H_DUMP_D','/W_BRAKE_GATE','/H_BRAKE_GATE','/W_GATE']:b.Delete(t)
 elif t.GetNetname()=='/+5V_MOTION' and (isinstance(t,k.PCB_VIA) and a[0]>30 or not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<.3 and not all(33<x<36 and 26<y<27 for x,y in [a,z])):b.Delete(t)
for a,z in [(q('Q10',4),q('R10',1)),(q('R10',1),q('R11',1))]:
 try:connect(b,'/W_GATE',a,z,[B],[B],(80,55),step=.05)
 except RuntimeError as e:print('BLOCKED GATE',e,flush=True)
 k.SaveBoard(str(p),b)
for net,ref,j,yy,w in [('W_DUMP_D','Q20','J11',10,1.5),('H_DUMP_D','Q40','J12',45,1.0)]:
 z=via(b,net,76.4,yy,vd=1,dr=.45,grid=False);track(b,net,[q(ref,3),z],.6,B)
 try:connect(b,'/'+net,z,q(j,1),[F,B],[F,B],(80,55),step=.1,width=w,vd=1,dr=.45)
 except RuntimeError as e:print('BLOCKED BRAKE',e,flush=True)
 k.SaveBoard(str(p),b)
