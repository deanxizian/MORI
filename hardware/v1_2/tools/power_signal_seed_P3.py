import pcbnew as k
from layout_P3 import paths,xy,pt,mm,track,F,B
name,d,p,r=paths('power');b=k.LoadBoard(str(p))
# Create another 0.10 mm of clearance without a detour in the power trunk.
for t in b.GetTracks():
 if t.GetNetname()=='/H_VM' and not isinstance(t,k.PCB_VIA):
  for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
   x,y=xy(get())
   if abs(x-40.175)<.001:setter(pt(40.075,y))
for f in b.GetFootprints():
 ref=f.GetReference()
 if not ref.startswith('U'):continue
 pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(p.GetPosition())[0],3) for p in pads))<=2 else 1
 for pad in pads:
  if not pad.GetNetname() or 'unconnected-' in pad.GetNetname():continue
  if ref in ['U60','U70'] and pad.GetNumber() not in ['1','5']:continue
  a=list(xy(pad.GetPosition()));z=list(a);z[axis]+=.8*(1 if a[axis]>[cx,cy][axis] else -1)
  track(b,pad.GetNet(),[a,z],.2,B if f.IsFlipped() else F)
k.SaveBoard(str(p),b)
