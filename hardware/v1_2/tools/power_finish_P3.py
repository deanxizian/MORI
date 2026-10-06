"""Open the gate corridor, reserve brake pulse current, and stitch local returns."""
import pcbnew as k,json,math,shutil
from layout_P3 import paths,xy,pt,mm,track,via,setplace,F,B,update_records
from route_local_P3 import connect
name,d,p,r=paths('power');b=k.LoadBoard(str(p));shutil.copy2(p,r/'before_finish.kicad_pcb');fps={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,n):return next(q for q in fps[ref].Pads() if q.GetNumber()==str(n))
setplace(fps['R11'],42.5,27,180,side='B')
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/W_GATE','/W_GATE_LOW','/W_DUMP_D','/H_DUMP_D']:b.Delete(t)
track(b,'W_GATE_LOW',[xy(pad('Q11',3).GetPosition()),xy(pad('R11',2).GetPosition())],.2,B)
log=[]
for a,z in [(('Q10',4),('R10',1)),(('Q10',4),('R11',1))]:
 try:log.append(connect(b,'/W_GATE',xy(pad(*a).GetPosition()),xy(pad(*z).GetPosition()),[B],[B],(80,55),step=.1))
 except RuntimeError as e:print('gate route blocked',str(e),flush=True)
for net,ref,j,yy,w in [('W_DUMP_D','Q20','J11',10,1.5),('H_DUMP_D','Q40','J12',45,1.0)]:
 z=via(b,net,76.25,yy,vd=1,dr=.45,grid=False);track(b,net,[xy(pad(ref,3).GetPosition()),z],.6,B)
 try:log.append(connect(b,'/'+net,z,xy(pad(j,1).GetPosition()),[F,B],[F,B],(80,55),step=.1,width=w,vd=1,dr=.45))
 except RuntimeError as e:print('brake route blocked',str(e),flush=True)
k.SaveBoard(str(p),b)
# Native shapes include copper on both sides; same-net pad clearance still applies to vias.
def via_clear(x,y,vd=.8):
 v=pt(x,y);radius=vd/2
 if not .6+radius<x<79.4-radius or not .6+radius<y<54.4-radius:return False
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
for ref,pn in [('C30',2),('J7',1),('JP60',2)]:
 q=pad(ref,pn);x,y=xy(q.GetPosition())
 for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  for dd in [1.3+i*.1 for i in range(15)]:
   target=(x+sx*dd,y+sy*dd)
   if not via_clear(*target):continue
   layers=[l for l in [F,B] if trace_clear((x,y),target,l)]
   if not layers:continue
   v=via(b,'GND',*target,grid=False)
   for layer in layers:track(b,'GND',[(x,y),v],.3,layer)
   stitched.append(dict(ref=ref,pin=pn,via=v,layers=layers));break
# Local 0.3 mm ground vias for both switching converters, including the input bypass.
for n in [60,70]:
 for ref,pn in [('U'+str(n),1),('C'+str(n),2),('C'+str(n+1),2),('C'+str(n+3),2),('C'+str(n+4),2),('R'+str(n+1),2)]:
  a=xy(pad(ref,pn).GetPosition());found=0
  candidates=sorted([(i*.15,j*.15) for i in range(-16,17) for j in range(-16,17) if (i or j)],key=lambda z:(z[0]*z[0]+z[1]*z[1],abs(z[1]),abs(z[0])))
  for dx,dy in candidates:
   target=(round(a[0]+dx,4),round(a[1]+dy,4))
   if not via_clear(*target) or not trace_clear(a,target,F,.3):continue
   v=via(b,'GND',*target,grid=False);track(b,'GND',[a,v],.3,F);stitched.append(dict(ref=ref,pin=pn,via=v,layers=[F]));found+=1
   if found==(2 if ref.startswith('U') else 1):break
  if not found:print('local ground stitch BLOCKED',ref,flush=True)
update_records('power',b,json.loads((d/'connectivity.json').read_text()));k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'power_finish.json').write_text(json.dumps(dict(routes=log,ground_stitches=stitched),indent=2)+'\n')
