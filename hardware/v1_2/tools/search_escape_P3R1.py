"""Search short outward escape alternatives without moving load conductors.

Hard obstacles: every pad/body/hole, every >=0.4 mm non-ground track, large
vias and already reserved ports from this pass. Thin obsolete signal copper
can be displaced and is logged for explicit reconnection and fresh DRC.
"""
import json,sys,math
import pcbnew as k
from layout_P3R1 import paths,xy,track,via,F,B
from geometry_guard_P3R1 import Guard,obstacles
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));protected=set();logs=[]
for spec in sys.argv[2:]:
 ref,num=spec.split(':');pad=next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==num);net=pad.GetNetname();origin=xy(pad.GetPosition());layer=pad.GetParentFootprint().GetLayer()
 print('Escape trial',kind,spec,net,flush=True)
 k.SaveBoard(str(p),b);hard=k.LoadBoard(str(p));movable=set()
 for t in list(hard.GetTracks()):
  uid=t.m_Uuid.AsString()
  if uid in protected:continue
  isvia=isinstance(t,k.PCB_VIA)
  if (isvia and k.ToMM(t.GetWidth(F))<.9) or (not isvia and k.ToMM(t.GetWidth())<=.4):movable.add(uid);hard.Delete(t)
 g=Guard(hard,net);best=None;trials=0
 for distance,end,route in g.portals(origin,layer,radius=4,step=.2):
  trials+=1
  if not .91<end[0]<({'motion':70,'power':80}[kind]-.91) or not .91<end[1]<({'motion':35,'power':55}[kind]-.91):continue
  bad=set();blocked=False
  for ll in [F,B]:
   for uid,info in obstacles(b,net,end,ll,.8,True):
    if uid not in movable:blocked=True;break
    bad.add(uid)
  if blocked:continue
  for a,z in zip(route,route[1:]):
   n=max(1,math.ceil(math.dist(a,z)/.08))
   for i in range(n+1):
    pos=(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n)
    for uid,info in obstacles(b,net,pos,layer):
     if uid not in movable:blocked=True;break
     bad.add(uid)
    if blocked:break
   if blocked:break
  if blocked:continue
  cost=sum(math.dist(a,z) for a,z in zip(route,route[1:]))+3*len(bad)
  if best is None or cost<best[0]:best=(cost,end,route,bad)
  if not bad or trials>=70:break
 if best is None:logs.append(dict(pin=spec,net=net,status='BLOCKED',trials=trials));print('NO LOCAL ESCAPE',spec,flush=True);continue
 _,end,route,bad=best;ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
 for uid in bad:
  if uid in ts:b.Delete(ts[uid])
 before={t.m_Uuid.AsString() for t in b.GetTracks()};track(b,net,route,.2,layer);via(b,net,*end,grid=False);protected|={t.m_Uuid.AsString() for t in b.GetTracks()}-before
 logs.append(dict(pin=spec,net=net,status='ROUTED',trials=trials,route=route,via=end,removed_uuids=sorted(bad),protected_new_uuids=sorted(protected-before)))
 print('Reserved',spec,'via',end,'length',round(sum(math.dist(a,z) for a,z in zip(route,route[1:])),2),'old fragments displaced',len(bad),flush=True)
 k.SaveBoard(str(p),b);(r/'searched_escape_ports.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2)+'\n')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
