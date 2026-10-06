"""Power corridors around the fixed rear switch and shell seating ledges."""
from layout_P5 import *
from geometry_guard_P5 import Guard,obstacles
n,d,p,r=paths('rear');b=k.LoadBoard(str(p));log=[]
(r/'before_rear_power_complete.kicad_pcb').write_bytes(p.read_bytes())
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/VBUS_RAW','/VBUS_FUSED']:b.Delete(t)
def add(net,ps,l,w=.6,newvia=False):
 g=Guard(b,net);checks=[g.line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])];vok=not newvia or g.via_clear(ps[-1],1.)
 print(net,ps,checks,'via',vok,flush=True)
 if not all(checks) or not vok:return
 track(b,net,ps,w,l)
 if newvia:via(b,net,*ps[-1],vd=1.,dr=.45,grid=False)
 log.append(dict(net=net,width=w,points=ps,layer=b.GetLayerName(l),new_via=newvia))
add('/VBUS_RAW',[(4.1,6.85),(4.1,7.7),(5.4,9.0),(7.1882,9)],B,newvia=True)
add('/VBUS_RAW',[(9.55,7.045),(9.55,8.5),(9.05,9),(7.1882,9)],B,w=.5)
add('/VBUS_RAW',[(14.45,7.045),(14.45,8.5),(14.95,9),(16.7,9)],B,w=.5,newvia=True)
add('/VBUS_RAW',[(7.1882,9),(7.1882,8.7),(7.6882,8.2),(16.2,8.2),(16.7,8.7),(16.7,9)],F)
add('/VBUS_FUSED',[(4.1,1.95),(4.1,1.45),(4.6,.95),(5.6,.95),(6.1,1.45),(6.1,3.31),(6.6,3.81),(7.0104,3.81)],B,newvia=True)
add('/VBUS_FUSED',[(7.0104,3.81),(6.596,3.81),(6.096,4.31),(6.096,16.1036)],F,newvia=True)
add('/VBUS_FUSED',[(6.096,16.1036),(16.7964,16.1036),(17.2,15.7),(19,15.7)],B)
add('/VBUS_FUSED',[(19.5,7.4),(19.5,7.8304),(16.9164,10.414)],B,newvia=True)
add('/VBUS_FUSED',[(16.9164,10.414),(17.2,10.6976),(17.2,15.7),(19,15.7)],F)
k.SaveBoard(str(p),b);(r/'rear_power_complete.json').write_text(json.dumps(log,indent=2)+'\n')
