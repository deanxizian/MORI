import pcbnew as k,json
from layout_P3 import paths,xy,pt,track,F,B
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/ARM_Q','/CLR_N','/IMU_CS'] or t.GetNetname()=='/GND' and not isinstance(t,k.PCB_VIA) and t.GetWidth()<k.FromMM(.299):b.Delete(t)
 # New direct signal link supersedes the old same-net via at the shifted resistor.
 elif isinstance(t,k.PCB_VIA) and t.GetNetname()=='/S288_TX_BUF':b.Delete(t)
for f in fps.values():
 if not f.GetReference().startswith('U') or f.GetReference()=='U100':continue
 pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(q.GetPosition())[0],3) for q in pads))<=2 else 1
 for q in pads:
  if q.GetNetname() not in ['/ARM_Q','/CLR_N','/IMU_CS']:continue
  a=list(xy(q.GetPosition()));z=list(a);z[axis]+=.6*(1 if a[axis]>[cx,cy][axis] else -1);track(b,q.GetNet(),[a,z],.2,B)
k.SaveBoard(str(p),b)
