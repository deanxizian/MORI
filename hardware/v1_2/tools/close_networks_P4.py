"""Connect separate copper clusters using existing outward escapes.

Native connectivity is rebuilt for each job, preventing duplicate parallel
paths from stale airwire pairs. Power use is only after explicit load routing;
these .2 mm routes must not be used as proof of a load-carrying connection.
"""
import sys,json,math
import pcbnew as k
from helpers_P4 import paths
from layout_P3R1 import xy,pt,track,via,F,B
from route_local_P4 import connect
from geometry_guard_P3R1 import Guard
from close_routes_P2 import merge_lines
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));j=json.loads((r/'drc.json').read_text());size={'motion':(70,35),'power':(80,55),'imu':(20,16),'rear':(24,25)}[kind]
items={x.m_Uuid.AsString():x for f in b.GetFootprints() for x in f.Pads()}
items.update({t.m_Uuid.AsString():t for t in b.GetTracks()})
def component(item):
 c=k.CONNECTIVITY_DATA();c.Build(b);net=item.GetNetCode();seen={};q=[item]
 while q:
  u=q.pop();uid=u.m_Uuid.AsString()
  if uid in seen or u.GetNetCode()!=net:continue
  seen[uid]=u;q.extend(c.GetConnectedTracks(u));q.extend(c.GetConnectedPads(u))
 return seen

def points(group):
 out={}
 for item in group.values():
  layers=tuple(l for l in [F,B] if item.IsOnLayer(l))
  positions=[xy(item.GetStart()),xy(item.GetEnd())] if isinstance(item,k.PCB_TRACK) and item.Type()!=k.PCB_VIA_T else [xy(item.GetPosition())]
  for pos in positions:out[pos]=tuple(sorted(set(out.get(pos,())+layers)))
 return out
log=[]
requested={s for s in sys.argv[2:] if s.startswith('/')}
rows=sorted(j['unconnected_items'],key=lambda row:(not any('/CLR_N' in q['description'] for q in row['items']),any('/CHG_N' in q['description'] for q in row['items'])))
for index,row in enumerate(rows):
 pair=[items.get(q['uuid']) for q in row['items']]
 if None in pair:continue
 a,z=pair;net=a.GetNetname()
 if requested and net not in requested:continue
 if net=='/GND' or (kind=='power' and net in ['/BAT_IN','/+5V_MOTION','/H_DUMP_D','/BAT_MON']):continue
 ac=component(a)
 if z.m_Uuid.AsString() in ac:continue
 zc=component(z)
 if len(ac)>len(zc):ac,zc=zc,ac
 ap,zp=points(ac),points(zc)
 candidates=list((math.dist(aa,zz),aa,zz,al,zl) for aa,al in ap.items() for zz,zl in zp.items())
 # Real layer-change ports are better destinations than a nearest loose tail
 # enclosed by existing copper. Do not repeatedly search the same pocket.
 vp={xy(t.GetPosition()) for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net}
 candidates.sort(key=lambda v: v[0])
 tried=set();done=False;reasons=[]
 print('Connecting',kind,index,net,'clusters',len(ac),len(zc),flush=True)
 for distance,aa,zz,al,zl in candidates:
  # Sample candidates from different points, not dozens of adjacent ends.
  key=(round(aa[0]*2),round(aa[1]*2),round(zz[0]*2),round(zz[1]*2))
  if key in tried:continue
  g=Guard(b,net)
  if not any(g.clear(aa,l) for l in al) or not any(g.clear(zz,l) for l in zl):continue
  tried.add(key)
  try:
   result=connect(b,net,aa,zz,list(al),list(zl),size,step=((.1 if distance>12 else .05) if "--fine" in sys.argv else .2),width=.2,vd=.8,dr=.3,max_nodes=350000,time_limit=25,heuristic_weight=2.0)
   log.append(dict(index=index,status='ROUTED',**result));done=True;break
  except RuntimeError as e:reasons.append(str(e))
  if len(tried)>=4:break
 if not done:log.append(dict(index=index,net=net,status='BLOCKED',reasons=reasons));print('BLOCKED CLUSTERS',net,reasons[-1:] or 'no clear endpoints',flush=True)
 k.SaveBoard(str(p),b);(r/'cluster_reconnections.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
