"""Move Q90 +1 mm in X before routing; parallel SOIC banks outside package."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import setplace,track,via,F,B
from geometry_guard_P3R1 import Guard
from body_keepouts_P3R1 import create
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_Q90_shift.kicad_pcb'),b)
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/PACK_FUSED','/BAT_IN'] or t.m_Uuid.AsString()=='9d3be9bd-c9bf-46c6-9bd4-153df8da1df7':b.Delete(t)
f=next(f for f in b.GetFootprints() if f.GetReference()=='Q90');setplace(f,6,11,0,'B');create(b)
log=[]
def add(n,ps,w,l):
 bad=[(a,z) for a,z in zip(ps,ps[1:]) if not Guard(b,n).line_clear(a,z,l,w)]
 if bad:print('BLOCKED',n,bad);return
 track(b,n,ps,w,l);log.append(dict(net=n,points=ps,width_mm=w,layer=l))
for y in [10.365,11.635,12.905]:add('/PACK_FUSED',[(3.525,y),(1.65,y)],.6,B)
add('/PACK_FUSED',[(1.65,10.6),(1.65,13)],1.6,B)
for y in [11,12,13]:
 assert Guard(b,'/PACK_FUSED').via_clear((1.65,y),1)
 via(b,'/PACK_FUSED',1.65,y,vd=1,dr=.45,grid=False)
for y in [9.095,10.365,11.635,12.905]:add('/BAT_IN',[(8.475,y),(9.2,y)],.6,B)
for y in [13.095,14.365,15.635,16.905]:add('/BAT_IN',[(10.525,y),(9.2,y)],.6,B)
add('/BAT_IN',[(9.2,10.2),(9.2,16.905)],1.5,B)
add('/BAT_IN',[(9.2,9.095),(9.2,10.2)],.6,B)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'master_corridor_shift.json').write_text(json.dumps(log,indent=2)+'\n')
