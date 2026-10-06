import pcbnew as k,json,shutil
from layout_P3 import paths,xy,pt,mm,setplace,track,area,update_records,F,B
from route_local_P3 import connect
name,d,p,r=paths('power');b=k.LoadBoard(str(r/'before_finish.kicad_pcb'));b.SetFileName(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
changes={'Q10':(42.5,22,0),'Q11':(31.5,15.5,0),'R10':(40.85,17.5,0),'R11':(37.7,15.5,180),'TP60':(40,16.5,0),'TP61':(43,16.5,0)}
log=[]
for ref,pos in changes.items():
 f=fps[ref];log.append(dict(ref=ref,before=[*xy(f.GetPosition()),f.GetOrientationDegrees()],after=pos));setplace(f,*pos,side='F' if ref.startswith('TP') else 'B')
rip=['/W_PRE','/W_GATE','/W_GATE_LOW','/ARM_Q','/WHEEL_ADC','/H_BRAKE_GATE']
for t in list(b.GetTracks()):
 a,z=xy(t.GetStart()),xy(t.GetEnd())
 if t.GetNetname() in rip or t.GetNetname()=='/W_VM' and t.GetLayer()==B and all(39<x<50 and 16<y<25 for x,y in [a,z]) or t.GetNetname() in ['/+5V_MOTION','/GND'] and any(mathdist<2 for mathdist in [((x-39.624)**2+(y-18.95)**2)**.5 for x,y in [a,z]]):b.Delete(t)
for z in list(b.Zones()):
 if z.GetIsRuleArea() and z.GetZoneName()=='OUTWARD_Q10':b.Delete(z)
area(b,'OUTWARD_Q10',B,[41.15,20,43.85,24])
def pin(ref,n):return next(q for q in fps[ref].Pads() if q.GetNumber()==str(n))
for net,x,ys,pins,w in [('W_PRE',38.225,[21.365,23.905],[1,2,3],1.5),('W_VM',46.775,[20.095,23.905],[5,6,7,8],1.5)]:
 for n in pins:
  a=xy(pin('Q10',n).GetPosition());track(b,net,[a,(x,a[1])],.6,B)
 track(b,net,[(x,ys[0]),(x,ys[1])],w,B)
track(b,'W_GATE_LOW',[xy(pin('Q11',3).GetPosition()),xy(pin('R11',2).GetPosition())],.2,B)
k.SaveBoard(str(p),b)
jobs=[('W_PRE',xy(pin('D10',1).GetPosition()),(38.225,22.635),1.5),('W_PRE',xy(pin('R10',2).GetPosition()),(38.225,22.635),.2),('W_VM',(46.775,20.095),xy(pin('C10',1).GetPosition()),1.5),('W_GATE',xy(pin('Q10',4).GetPosition()),xy(pin('R10',1).GetPosition()),.2),('W_GATE',xy(pin('R10',1).GetPosition()),xy(pin('R11',1).GetPosition()),.2)]
for net,a,z,w in jobs:
 try:connect(b,'/'+net,a,z,[B],[B],(80,55),step=.1,width=w,vd=.8 if w==.2 else 1,dr=.3 if w==.2 else .45)
 except RuntimeError as e:print('BLOCKED',net,str(e),flush=True)
 k.SaveBoard(str(p),b)
update_records('power',b,json.loads((d/'connectivity.json').read_text()));k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'wheel_switch_rotation.json').write_text(json.dumps(log,indent=2)+'\n')
