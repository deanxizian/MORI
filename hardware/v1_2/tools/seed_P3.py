"""P3 deliberate high-current and local fanout copper. No P2 file is written."""
import sys,json,math
import pcbnew as k
from layout_P3 import paths,pt,mm,xy,track,via,F,B,area

def seed(kind):
 name,d,pcb,r=paths(kind);b=k.LoadBoard(str(pcb));fps={f.GetReference():f for f in b.GetFootprints()}
 for t in list(b.GetTracks()):b.Delete(t)
 for z in list(b.Zones()):
  if not z.GetIsRuleArea():b.Delete(z)
 def pin(ref,num):return next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))
 def route(ref,num,points,width=.2,layer=None):
  p=pin(ref,num);return track(b,p.GetNet(),[xy(p.GetPosition())]+points,width,layer if layer is not None else B if fps[ref].IsFlipped() else F)
 if kind=='imu':
  for p in fps['U1'].Pads():
   n=int(p.GetNumber());a=xy(p.GetPosition());dx,dy=(-1,0) if n<=4 else (0,1) if n<=7 else (1,0) if n<=11 else (0,-1)
   track(b,p.GetNet(),[a,(a[0]+dx,a[1]+dy)],.2,F)
 if kind=='motion':
  for f in fps.values():
   if not f.GetReference().startswith('U') or f.GetReference()=='U100':continue
   pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(p.GetPosition())[0],3) for p in pads))<=2 else 1
   for p in pads:
    if not p.GetNetname() or 'unconnected-' in p.GetNetname():continue
    a=list(xy(p.GetPosition()));z=list(a);z[axis]+=.8*(1 if a[axis]>[cx,cy][axis] else -1)
    track(b,p.GetNet(),[a,z],.2,B)
  made=set()
  for p in fps['U100'].Pads():
   if p.GetNetname()!='/GND':continue
   x,y=xy(p.GetPosition())
   for dx,dy in [(-1.27,-1.27),(-1.27,1.27),(1.27,-1.27),(1.27,1.27)]:
    z=(round(x+dx,5),round(y+dy,5))
    for layer in [F,B]:track(b,p.GetNet(),[(x,y),z],.3,layer)
    if z not in made:via(b,p.GetNet(),*z,vd=.75,dr=.25,grid=False);made.add(z)
 if kind=='power':
  for c in ['D10','D30']:fps[c].SetField('Datasheet','')
  for n,uy in [(60,23),(70,43)]:
   u='U'+str(n);l='L'+str(n);nn='M5' if n==60 else 'C5';out='+5V_MOTION' if n==60 else '+5V_CAM'
   # Flip lower divider so FB leaves away from the high-current output pads.
   fps['R'+str(n+1)].SetOrientationDegrees(0)
   # Switch node: single short F.Cu path, never below U60/U70.
   route(u,2,[(26.225,uy),(23.225,uy-3)],.6)
   route(l,1,[(23.225,uy-4.5),(24.225,uy-5.5),(29.225,uy-5.5),(30.225,uy-4.5),(30.225,uy-3.5)],.2)
   route(u,6,[(31.35,uy-3.075),(31.775,uy-3.5)],.2)
   # Input decoupling, outward left from VIN. Bulk is connected separately.
   route(u,3,[(26.725,uy+.95),(26.725,uy+2.8)],.6)
   route('C'+str(n+1),1,[(24.675,uy+2.8),(24.475,uy+3)],.8)
   # Output L/C path; the feedback branch is intentionally a separate thin takeoff.
   route(l,2,[(17.775,uy-8.3),(18,uy-8.525),(22,uy-8.525)],1.0)
   # Local feedback network, with 90-degree T junctions rather than acute joins.
   route(u,4,[(32.5,uy+.95),(32.5,uy+1.725),(33.5,uy+1.725)],.2)
   route('C'+str(n+5),2,[(35.45,uy+1.725),(35.5,uy+1.675)],.2)
   track(b,nn+'_FB',[(32.5,uy+1.725),(32.5,uy+5),(33.675,uy+5)],.2,F)
   route('C'+str(n+5),1,[(35.45,uy+3.275),(35.5,uy+3.325)],.2)
  for ref in ['Q1','Q10','Q30']:
   f=fps[ref];x,y=xy(f.GetPosition());dx,dy=(2.0,1.35) if ref=='Q10' else (1.35,2.0)
   area(b,'OUTWARD_'+ref,B,[x-dx,y-dy,x+dx,y+dy])
  for ref in ['L60','L70']:
   x,y=xy(fps[ref].GetPosition());area(b,'NO_UNDER_INDUCTOR_'+ref,F,[x-.9,y-2.8,x+.9,y+2.8])
  # Parallel power MOSFET pad banks use broad outward buses. Gate pads remain separate.
  for ref,banks,width in [('Q1',[[1,2,3],[5,6,7,8]],2.0),('Q10',[[1,2,3],[5,6,7,8]],1.5),('Q30',[[1,2,3],[5,6,7,8]],1.0)]:
   f=fps[ref];cx,cy=xy(f.GetPosition())
   for bank in banks:
    pads=[pin(ref,n) for n in bank];poss=[xy(p.GetPosition()) for p in pads]
    if max(x for x,y in poss)-min(x for x,y in poss)<.01:
     x=poss[0][0];sgn=1 if x>cx else -1;bus=x+sgn*(1.2 if ref=='Q30' else 1.6 if ref=='Q1' else 1.8)
     for p in pads:track(b,p.GetNet(),[xy(p.GetPosition()),(bus,xy(p.GetPosition())[1])],.6,B)
     track(b,pads[0].GetNet(),[(bus,min(y for x,y in poss)),(bus,max(y for x,y in poss))],width,B)
    else:
     y=poss[0][1];sgn=1 if y>cy else -1;bus=y+sgn*1.8
     for p in pads:track(b,p.GetNet(),[xy(p.GetPosition()),(xy(p.GetPosition())[0],bus)],.6,B)
     track(b,pads[0].GetNet(),[(min(x for x,y in poss),bus),(max(x for x,y in poss),bus)],width,B)
  # Shunt Kelvin pickups from INNER pad edges, independent of the outer load trunks.
  route('R2',1,[(22.5,15),(22.5,16.675),(21,18.175)],.2,B)
  route('R2',2,[(27.5,15),(27.5,16.675),(29,18.175)],.2,B)
 k.SaveBoard(str(pcb),b)
 print(name,'reserved local copper',len(b.GetTracks()),flush=True)

if __name__=='__main__':seed(sys.argv[1])
