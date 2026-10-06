import pcbnew as k,json,math,sys
from layout_P3 import paths,xy,pt,mm,via,track,F,B
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,n):return next(q for q in fps[ref].Pads() if q.GetNumber()==str(n))
def via_clear(x,y,vd=.8):
 v=pt(x,y);radius=vd/2
 w,h={'motion':(70,35),'power':(80,55)}[kind]
 if not .6+radius<x<w-.6-radius or not .6+radius<y<h-.6-radius:return False
 for f in fps.values():
  for q in f.Pads():
   for layer in [F,B]:
    if q.IsOnLayer(layer) and q.GetEffectiveShape(layer).Collide(v,mm(radius+.205)):return False
 for t in b.GetTracks():
  if t.GetNetname()=='/GND':
   if isinstance(t,k.PCB_VIA) and math.dist(xy(t.GetPosition()),(x,y))<.82:return False
   continue
  for layer in [F,B]:
   if t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(v,mm(radius+.205)):return False
 for z in b.Zones():
  if z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Collide(v,mm(radius+.002)):return False
 return True

def trace_clear(a,z,layer,width=.3):
 shapes=[]
 for f in fps.values():
  for q in f.Pads():
   if q.IsOnLayer(layer) and q.GetNetname()!='/GND':shapes.append((q.GetEffectiveShape(layer),width/2+.205))
 for t in b.GetTracks():
  if t.IsOnLayer(layer) and t.GetNetname()!='/GND':shapes.append((t.GetEffectiveShape(layer),width/2+.205))
 for q in b.Zones():
  if q.GetIsRuleArea() and q.IsOnLayer(layer) and q.GetDoNotAllowTracks():shapes.append((q.Outline(),width/2+.002))
 n=max(1,math.ceil(math.dist(a,z)/.03))
 return not any(shape.Collide(pt(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n),mm(cl)) for i in range(n+1) for shape,cl in shapes)
stitched=[]
refs=[('C'+str(n),2) for n in range(1,8)] if kind=='motion' else [('U60',1),('U70',1),('C60',2),('C70',2),('C61',2),('C71',2),('C63',2),('C73',2),('C64',2),('C74',2),('R61',2),('R71',2)]
for ref,pn in refs:
 q=pad(ref,pn);a=xy(q.GetPosition());layer=B if fps[ref].IsFlipped() else F
 assert q.GetNetname()=='/GND',(ref,pn)
 candidates=sorted([(i*.2,j*.2) for i in range(-15,16) for j in range(-15,16) if (i or j) and (not i or not j or abs(i)==abs(j))],key=lambda z:(z[0]*z[0]+z[1]*z[1],abs(z[1]),abs(z[0])))
 for dx,dy in candidates:
  target=(round(a[0]+dx,4),round(a[1]+dy,4))
  if not via_clear(*target) or not trace_clear(a,target,layer,.3):continue
  v=via(b,'GND',*target,grid=False);track(b,'GND',[a,v],.3,layer);stitched.append(dict(ref=ref,pin=pn,via=v,layer=layer));break
 else:print('stitch blocked',ref,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'ground_stitch.json').write_text(json.dumps(stitched,indent=2)+'\n');print(kind,'ground stitches',len(stitched),flush=True)
