"""Reconnect selected signal clusters by displacing a few obstructing fragments.

Pads, package keepouts, load copper, large vias and pad-attached escape tracks
remain hard obstacles. Every displaced UUID/net is recorded for reconnection.
This is an editing aid; actual KiCad checks are mandatory afterwards.
"""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,F,B,mm
from route_local_P3R1 import connect

kind=sys.argv[1];name,d,p,r=paths(kind);wanted=['/'+n.lstrip('/') for n in sys.argv[2:]]
b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());size={'motion':(70,35),'power':(80,55)}[kind]
log=[];completed=set()
critical={'/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/KELVIN_P','/KELVIN_N'}
def group(item):
 c=k.CONNECTIVITY_DATA();c.Build(b);seen={};q=[item]
 while q:
  x=q.pop();uid=x.m_Uuid.AsString()
  if uid in seen or x.GetNetCode()!=item.GetNetCode():continue
  seen[uid]=x;q.extend(c.GetConnectedTracks(x));q.extend(c.GetConnectedPads(x))
 return seen
def points(g):
 out={}
 for x in g.values():
  ll=tuple(l for l in [F,B] if x.IsOnLayer(l))
  pp=[xy(x.GetStart()),xy(x.GetEnd())] if isinstance(x,k.PCB_TRACK) and x.Type()!=k.PCB_VIA_T else [xy(x.GetPosition())]
  for pos in pp:out[pos]=tuple(sorted(set(out.get(pos,())+ll)))
 return out
def order(row):
 return next((i for i,n in enumerate(wanted) if any('['+n+']' in q['description'] for q in row['items'])),len(wanted))
for row in sorted(j['unconnected_items'],key=order):
 items={x.m_Uuid.AsString():x for f in b.GetFootprints() for x in f.Pads()};items.update({x.m_Uuid.AsString():x for x in b.GetTracks()})
 pair=[items.get(i['uuid']) for i in row['items']]
 if None in pair:continue
 a,z=pair;net=a.GetNetname()
 if net not in wanted:continue
 ga=group(a)
 if z.m_Uuid.AsString() in ga:continue
 gz=group(z);ap,zp=points(ga),points(gz)
 candidates=list((math.dist(aa,zz),aa,zz,al,zl) for aa,al in ap.items() for zz,zl in zp.items())
 vp={xy(t.GetPosition()) for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net}
 candidates.sort(key=lambda v:(-(int(v[1] in vp)+int(v[2] in vp)),v[0]))
 k.SaveBoard(str(p),b);hard=k.LoadBoard(str(p));movable={};soft=[]
 pads=[q for f in b.GetFootprints() for q in f.Pads()]
 for t in list(hard.GetTracks()):
  if t.GetNetname()==net:continue
  if kind=='power' and t.GetNetname() in critical:continue
  if t.GetNetname() in completed:continue
  v=isinstance(t,k.PCB_VIA)
  if (v and k.ToMM(t.GetWidth(F))>=.9) or (not v and k.ToMM(t.GetWidth())>.25):continue
  if not v and any(q.GetNetCode()==t.GetNetCode() and q.IsOnLayer(t.GetLayer()) and t.GetEffectiveShape(t.GetLayer()).Collide(q.GetEffectiveShape(t.GetLayer()),mm(.05)) for q in pads):continue
  movable[t.m_Uuid.AsString()]=dict(net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd()))
  for l in [F,B]:
   if t.IsOnLayer(l):soft.append((t.GetEffectiveShape(l).Clone(),l))
  hard.Delete(t)
 original_ids={t.m_Uuid.AsString() for t in hard.GetTracks()};done=False
 for _,aa,zz,al,zl in candidates[:6]:
  try:
   result=connect(hard,net,aa,zz,list(al),list(zl),size,step=.1,vd=(.8 if kind=='motion' else .6),dr=.3,time_limit=55,max_nodes=900000,heuristic_weight=1.5,soft_shapes=soft)
  except RuntimeError as exc:print('trial',net,str(exc),flush=True);continue
  new=[t for t in hard.GetTracks() if t.m_Uuid.AsString() not in original_ids];bad=set()
  for t in new:
   for q in b.GetTracks():
    uid=q.m_Uuid.AsString()
    if uid not in movable or q.GetNetname()==net:continue
    for l in [F,B]:
     if t.IsOnLayer(l) and q.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l),mm(.205)):bad.add(uid);break
  if len({movable[u]['net'] for u in bad})>5:
   for t in new:hard.Delete(t)
   print('reject excessive displaced nets',net,len(bad),flush=True);continue
  ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
  for uid in bad:b.Delete(ts[uid])
  for t in new:
   c=t.Duplicate();b.Add(c)
  log.append(dict(**result,removed={u:movable[u] for u in sorted(bad)}));done=True;completed.add(net)
  print('RIPUP ROUTE',net,'displaced',len(bad),'items',sorted({movable[u]['net'] for u in bad}),flush=True);break
 if not done:log.append(dict(net=net,status='BLOCKED'))
 k.SaveBoard(str(p),b);(r/'ripup_reconnections.json').write_text(json.dumps(log,indent=2)+'\n')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
