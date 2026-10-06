import pcbnew as k,json
from layout_P3 import paths,xy,pt,setplace,track,update_records,F,B
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
setplace(fps['R11'],37.7,16.75,180,side='B')
for t in list(b.GetTracks()):
 a,z=xy(t.GetStart()),xy(t.GetEnd());local=all(17<x<30 and 23<y<31 for x,y in [a,z])
 if t.GetNetname() in ['/W_GATE','/W_GATE_LOW'] or t.GetNetname()=='/M5_VIN' and (isinstance(t,k.PCB_VIA) or t.GetLayer()==B or not local):b.Delete(t)
def q(ref,n):return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==str(n)).GetPosition())
jobs=[('W_GATE_LOW',q('Q11',3),q('R11',2),[B],[B],.2),('W_GATE',q('Q10',4),q('R10',1),[B],[B],.2),('W_GATE',q('R10',1),q('R11',1),[B],[B],.2),('M5_VIN',q('F60',2),q('C60',1),[F],[F],.8)]
for nn,a,z,al,zl,w in jobs:
 try:connect(b,'/'+nn,a,z,al,zl,(80,55),step=.1,width=w,vd=.8 if w==.2 else 1,dr=.3 if w==.2 else .45)
 except RuntimeError as e:print('BLOCKED',nn,str(e),flush=True)
 k.SaveBoard(str(p),b)
update_records('power',b,json.loads((d/'connectivity.json').read_text()));k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
