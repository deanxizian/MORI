"""Reserve straight, body-outward connector escapes before other signals."""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,F,B
from geometry_guard_P3R1 import obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};log=[]
for ref in ['J7']:
 f=fps[ref]
 for pad in f.Pads():
  if not pad.GetNumber().isdigit() or (pad.GetNetname()=='/GND' or 'unconnected-' in pad.GetNetname()):continue
  net=pad.GetNetname();a=xy(pad.GetPosition());made=False
  for length in [1.5,1.6,1.65,1.55]:
   z=(a[0],a[1]-length) if ref=='J7' else (a[0]+length,a[1])
   if not .91<z[0]<69.09 or not .91<z[1]<34.09:continue
   tracks={t.m_Uuid.AsString():t for t in b.GetTracks()};bad=set();block=[]
   for layer in [F,B]:
    for uid,info in obstacles(b,net,z,layer,.8,True):
     if uid in tracks:bad.add(uid)
     else:block.append((uid,info))
   for i in range(51):
    pos=(a[0]+(z[0]-a[0])*i/50,a[1]+(z[1]-a[1])*i/50)
    for uid,info in obstacles(b,net,pos,F,.2):
     if uid in tracks:bad.add(uid)
     else:block.append((uid,info))
   if block:continue
   # Prevent nearly duplicate same-net drill holes; reuse an exact one.
   own=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),z)<.81]
   if any(math.dist(xy(t.GetPosition()),z)>.001 for t in own):continue
   for uid in bad:b.Delete(tracks[uid])
   track(b,net,[a,z],.2,F)
   if not own:via(b,net,*z,grid=False)
   log.append(dict(ref=ref,pin=pad.GetNumber(),net=net,outward_via_mm=z,old_copper_removed=sorted(bad),status='ROUTED'));made=True;break
  if not made:log.append(dict(ref=ref,pin=pad.GetNumber(),net=net,status='BLOCKED',obstacles=block));print('blocked port',ref,pad.GetNumber(),block,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'J7_outward_vias.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n');print('Reserved connector escapes',sum(x['status']=='ROUTED' for x in log),'of',len(log),flush=True)
