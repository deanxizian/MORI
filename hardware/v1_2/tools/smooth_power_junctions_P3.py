"""Replace overlap/T-junction artifacts with deliberate entries; preserve rules."""
import pcbnew as k,json
from layout_P3 import paths,xy,pt,F,B,track
from geometry_guard_P3 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));ts={t.m_Uuid.AsString():t for t in b.GetTracks()};log=[]
remove=['d7f0cebf-787d-443e-b219-9b7ae530d905','a83192b5-3e71-428a-b8d2-92e8bb252d11','42a5b4ff-e635-4530-8533-93102cfeac8a','53c9d816-fe74-4198-bf87-7fe8ead55e75','16109e2a-0d44-433e-8b6d-d951f894d720']
for uid in remove:
 if uid in ts:b.Delete(ts[uid])
if '0ea3e3b3-7a91-4424-b89b-81ca5f4470ea' in ts:ts['0ea3e3b3-7a91-4424-b89b-81ca5f4470ea'].SetStart(pt(36.525,48))
if '92b33481-349f-4183-ad83-8f4f45eb5f2d' in ts:ts['92b33481-349f-4183-ad83-8f4f45eb5f2d'].SetStart(pt(25.45,24.75))
for uid,net,points,width in [
 ('e2054f5a-7422-4714-ac8e-bca729a7f7b7','/BAT_IN',[(10.7,12.6),(9.42,12.6),(8.925,13.095)],2),
 ('a0606de4-bd8a-4ce5-b244-5b6b975a649f','/W_PRE',[(41.3,25.7),(40.02,25.7),(38.225,23.905)],1.5),
 ('ae76f214-a006-4f90-9cdf-3410c10d7d9d','/WHEEL_ADC',[(50.5,27),(50.5,27.5),(46.9,31.1)],.2)]:
 if uid not in ts:continue
 g=Guard(b,net)
 if all(g.line_clear(a,z,B,width) for a,z in zip(points,points[1:])):
  b.Delete(ts[uid]);track(b,net,points,width,B);log.append(dict(net=net,points=points))
  if net=='/WHEEL_ADC':
   for t in b.GetTracks():
    if t.GetNetname()==net and not isinstance(t,k.PCB_VIA):
     if xy(t.GetStart())==(46.9,30.6):t.SetStart(pt(46.9,31.1))
     if xy(t.GetEnd())==(46.9,30.6):t.SetEnd(pt(46.9,31.1))
 else:print('needs alternate junction',net,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'smooth_junctions.json').write_text(json.dumps(log,indent=2)+'\n')
