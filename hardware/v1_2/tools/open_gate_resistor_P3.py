import pcbnew as k,json,itertools,math
from layout_P3 import paths,xy,pt,F,B,via,track,setplace
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};fp=fps['R11'];log=[]
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/W_GATE','/W_GATE_LOW']:b.Delete(t)
chosen=None
for dx,dy in sorted([(i*.5,j*.5) for i in range(-6,7) for j in range(-6,7)],key=lambda v:v[0]**2+v[1]**2):
 for angle in [90,270,0,180]:
  setplace(fp,37.7+dx,16.75+dy,angle,'B');pads={q.GetNumber():q for q in fp.Pads()}
  if not all(Guard(b,str(q.GetNetname())).clear(xy(q.GetPosition()),B,.9) for q in pads.values()):continue
  a=xy(pads['2'].GetPosition());centre=xy(fp.GetPosition());options=list(itertools.islice(Guard(b,'/W_GATE_LOW').portals(a,B,3),30));options=[o for o in options if (o[1][0]-a[0])*(a[0]-centre[0])+(o[1][1]-a[1])*(a[1]-centre[1])>=0]
  if options:chosen=options[0];break
 if chosen:break
assert chosen,'R11 no outward portal';print('R11',xy(fp.GetPosition()),fp.GetOrientationDegrees(),flush=True)
_,target,route=chosen;via(b,'W_GATE_LOW',*target,grid=False);track(b,'W_GATE_LOW',route,.2,B)
a=(32.9375,12.5);options=list(itertools.islice(Guard(b,'/W_GATE_LOW').portals(a,B,4),30));options=[o for o in options if o[1][0]>a[0]];assert options
_,source,route=options[0];via(b,'W_GATE_LOW',*source,grid=False);track(b,'W_GATE_LOW',route,.2,B);k.SaveBoard(str(p),b)
log.append(connect(b,'/W_GATE_LOW',source,target,[F,B],[F,B],(80,55),step=.1));k.SaveBoard(str(p),b)
for a,z in [((40.025,20.095),(40.025,17.5)),(xy(pads['1'].GetPosition()),(40.025,17.5))]:
 try:log.append(connect(b,'/W_GATE',a,z,[B],[B],(80,55),step=.05));k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'gate_resistor_open.json').write_text(json.dumps(dict(R11_xy=xy(fp.GetPosition()),rotation=fp.GetOrientationDegrees(),routes=log),indent=2)+'\n')
