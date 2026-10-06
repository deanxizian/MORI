import pcbnew as k,itertools,json,math
from layout_P3 import paths,xy,pt,F,B,track,via,setplace
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};fp=fps['Q11'];oldg=pt(30.5625,14.55)
for t in list(b.GetTracks()):
 if t.GetNetname()=='/W_GATE_LOW' or (t.GetNetname()=='/GND' and (t.GetStart()==oldg or t.GetEnd()==oldg)):b.Delete(t)
chosen=None;trials=[]
for dx,dy in sorted([(i*.5,j*.5) for i in range(-12,13) for j in range(-12,13)],key=lambda v:v[0]**2+v[1]**2):
 for angle in [90,270,180,0]:
  setplace(fp,31.5+dx,15.5+dy,angle,'B');pads={q.GetNumber():q for q in fp.Pads()};good=all(Guard(b,str(q.GetNetname())).clear(xy(q.GetPosition()),B,.8) for q in pads.values())
  options=list(itertools.islice(Guard(b,'/ARM_Q').portals(xy(pads['1'].GetPosition()),B,3),1)) if good else []
  trials.append(dict(centre=xy(fp.GetPosition()),angle=angle,pads_clear=good,escape=options))
  if options:chosen=options[0];break
 if chosen:break
assert chosen,'no clear Q11 orientation'
print('Q11',xy(fp.GetPosition()),fp.GetOrientationDegrees(),flush=True);_,vp,route=chosen;via(b,'ARM_Q',*vp,grid=False);track(b,'ARM_Q',route,.2,B)
k.SaveBoard(str(p),b);log=[]
for net,a,z,al,zl in [('/ARM_Q',vp,(42,28.15),[F,B],[F,B]),('/W_GATE_LOW',xy(pads['3'].GetPosition()),(36.875,16.75),[B],[B])]:
 try:log.append(connect(b,net,a,z,al,zl,(80,55),step=.05));k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True);log.append(dict(net=net,error=str(e)))
# Restore a local return after rotating the package, if a useful portal exists.
a=xy(pads['2'].GetPosition());options=list(itertools.islice(Guard(b,'/GND').portals(a,B,3),1))
if options:
 _,vp,route=options[0];via(b,'GND',*vp,grid=False);track(b,'GND',route,.2,B)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'gate_control_rotation.json').write_text(json.dumps(dict(trials=trials,routes=log),indent=2)+'\n')
