import pcbnew as k,json,itertools,math
from layout_P3 import paths,xy,pt,F,B,via,track,setplace
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/W_GATE','/W_GATE_LOW']:b.Delete(t)
setplace(fps['R11'],43.5,11.5,0,'B');rp={q.GetNumber():q for q in fps['R11'].Pads()}
for q in rp.values():assert Guard(b,str(q.GetNetname())).clear(xy(q.GetPosition()),B,.95)
log=[];portals={}
for name,net,a,direction in [('Q11','/W_GATE_LOW',(32.9375,12.5),(1,0)),('R11_LOW','/W_GATE_LOW',xy(rp['2'].GetPosition()),(1,0)),('R11_GATE','/W_GATE',xy(rp['1'].GetPosition()),(-1,0)),('R10','/W_GATE',(40.025,17.5),(-1,0))]:
 g=Guard(b,net);ops=list(g.portals(a,B,5));ops=[o for o in ops if (o[1][0]-a[0])*direction[0]+(o[1][1]-a[1])*direction[1]>=0];assert ops,('no escape',name)
 _,v,route=ops[0];via(b,net,*v,grid=False);track(b,net,route,.2,B);portals[name]=v;log.append(dict(ref=name,net=net,route=route,via=v));print(name,v,flush=True)
assert Guard(b,'/W_GATE').line_clear((40.025,20.095),portals['R10'],B)
track(b,'W_GATE',[(40.025,20.095),portals['R10']],.2,B)
k.SaveBoard(str(p),b)
for net,a,z in [('/W_GATE_LOW',portals['Q11'],portals['R11_LOW']),('/W_GATE',portals['R10'],portals['R11_GATE'])]:
 try:log.append(connect(b,net,a,z,[F,B],[F,B],(80,55),step=.1));k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True);log.append(dict(net=net,error=str(e)))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'free_gate_bay.json').write_text(json.dumps(log,indent=2)+'\n')
