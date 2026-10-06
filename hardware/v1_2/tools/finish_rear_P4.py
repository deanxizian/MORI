"""Documented outward USB escape and VBUS necks; review with native DRC."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import track,via,F,B
from geometry_guard_P3R1 import Guard,obstacles
name,d,p,r=paths('rear');b=k.LoadBoard(str(p));log=[]
def add(net,points,width,layer):
 g=Guard(b,net);bad=[]
 for a,z in zip(points,points[1:]):
  if not g.line_clear(a,z,layer,width):bad.append([a,z])
 if bad:
  log.append(dict(net=net,status='BLOCKED',segments=bad));print(net,'BLOCKED',bad);return False
 track(b,net,points,width,layer);log.append(dict(net=net,points=points,width=width,layer=layer,status='ADDED'));return True
add('/CC1',[(10.75,7.045),(10.75,8.1),(11.05,8.4),(11.05,9.5)],.2,B)
add('/CC2',[(13.75,7.045),(13.75,7.8),(12.95,8.6),(12.95,9.5)],.2,B)
add('/VBUS_RAW',[(9.55,7.045),(9.55,7.7),(8.85,8.4)],.4,B)
add('/VBUS_RAW',[(8.85,8.4),(7.1,8.4)],.6,B)
add('/VBUS_RAW',[(14.45,7.045),(14.45,7.7),(15.15,8.4)],.4,B)
add('/VBUS_RAW',[(15.15,8.4),(16.9,8.4)],.6,B)
for x in [7.1,16.9]:
 if Guard(b,'/VBUS_RAW').via_clear((x,8.4)):
  via(b,'/VBUS_RAW',x,8.4,grid=False);log.append(dict(via=[x,8.4],net='/VBUS_RAW'))
 else:print('BLOCKED via',x,[obstacles(b,'/VBUS_RAW',(x,8.4),l,.8,True) for l in [F,B]])
add('/VBUS_RAW',[(7.1,8.4),(8.4,7.1),(15.6,7.1),(16.9,8.4)],.6,F)
add('/VBUS_RAW',[(7.1,8.4),(4,8.4),(4,7.25)],.6,B)
add('/VBUS_RAW',[(7.1,8.4),(6.7,8.8),(6.7,21.7),(8,23)],.2,F)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'manual_USB_escape.json').write_text(json.dumps(log,indent=2)+'\n')
