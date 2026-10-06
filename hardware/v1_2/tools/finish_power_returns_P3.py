import pcbnew as k,json,math,itertools
from layout_P3 import paths,xy,pt,F,B,via,track
from geometry_guard_P3 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};log=[]
for ref,pn in [('C30','2'),('J7','1'),('JP60','2')]:
 q=[q for q in fps[ref].Pads() if q.GetNumber()==pn][0];a=xy(q.GetPosition())
 for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  g=Guard(b,'/GND')
  for dd in [1.3+i*.1 for i in range(22)]:
   v=(round(a[0]+sx*dd,5),round(a[1]+sy*dd,5))
   if not g.via_clear(v):continue
   layers=[l for l in [F,B] if g.line_clear(a,v,l,.3)]
   if not layers:continue
   via(b,'GND',*v,grid=False)
   for l in layers:track(b,'GND',[a,v],.3,l)
   log.append(dict(ref=ref,corner=[sx,sy],via=v,layers=layers));break
  else:print('thermal corner blocked',ref,sx,sy,flush=True)
# Newly relocated divider returns to the plane locally.
a=(52.825,27);g=Guard(b,'/GND');choices=list(itertools.islice(g.portals(a,B,3),1))
if choices:
 _,v,route=choices[0];via(b,'GND',*v,grid=False);track(b,'GND',route,.2,B);log.append(dict(ref='R53',via=v))
# Parallel current-transfer via, connected on BOTH copper layers.
a=(15.4,11.5);g=Guard(b,'/BAT_MON');candidates=[]
for i in range(-20,21):
 for j in range(-20,21):
  v=(round(a[0]+i*.1,5),round(a[1]+j*.1,5))
  if math.dist(a,v)<1 or not g.via_clear(v,1):continue
  if all(g.line_clear(a,v,l,1) for l in [F,B]):candidates.append((math.dist(a,v),v))
if candidates:
 v=min(candidates)[1];via(b,'BAT_MON',*v,vd=1,dr=.45,grid=False)
 for l in [F,B]:track(b,'BAT_MON',[a,v],1,l)
 log.append(dict(ref='BAT_MON parallel barrel',via=v));print('parallel battery via',v,flush=True)
else:print('parallel battery via needs alternate corridor',flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'final_returns.json').write_text(json.dumps(log,indent=2)+'\n')
