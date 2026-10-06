"""Shift the switch/PH4 inward 0.8/0.5 mm to free outward USB escape."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import setplace,track,via,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
name,d,p,r=paths('rear');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_rear_corridors.kicad_pcb'),b)
# Preserve CC1's short documented escape; reconnect other small board nets afresh.
for t in list(b.GetTracks()):
 b.Delete(t)
f={x.GetReference():x for x in b.GetFootprints()};setplace(f['SW1'],12,12.9,0,'F');setplace(f['J3'],9,19,0,'F');setplace(f['D2'],10.75,10.5,270,'B');setplace(f['D3'],13.75,10.5,270,'B');create(b)
log=[]
def add(net,ps,w,l):
 assert all(Guard(b,net).line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])),(net,ps)
 track(b,net,ps,w,l);log.append(dict(net=net,points=ps,width_mm=w,layer=l))
add('/CC1',[(10.75,7.045),(10.75,9.45)],.2,B)
add('/CC2',[(13.75,7.045),(13.75,9.45)],.2,B)
for x in [9.55,14.45]:
 add('/VBUS_RAW',[(x,7.045),(x,8.4)],.4,B)
 # Same-net via beside the USB power land; native DRC checks hole clearance.
 via(b,'/VBUS_RAW',x,8.4,vd=.75,dr=.25,grid=False)
add('/VBUS_RAW',[(9.55,8.4),(14.45,8.4)],.6,F)
k.SaveBoard(str(p),b);(r/'USB_escape_priority.json').write_text(json.dumps(log,indent=2)+'\n')
