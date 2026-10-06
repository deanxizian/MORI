"""Manual rear-board power paths reserved before signal routing."""
from layout_P5 import *
from geometry_guard_P5 import Guard,obstacles
from body_P5 import create
n,d,p,r=paths('rear');b=k.LoadBoard(str(p));log=[]
# Only new P5 power nets are reconstructed; no previous-board copper imported.
for t in list(b.GetTracks()):b.Delete(t)
fs={f.GetReference():f for f in b.GetFootprints()}
setplace(fs['F1'],4.1,4.4,90,'B')
create(b,'rear')
def add(net,ps,layer,via_end=False,w=.6):
 g=Guard(b,net);ok=[g.line_clear(a,z,layer,w) for a,z in zip(ps,ps[1:])]
 vok=not via_end or g.via_clear(ps[-1],1.)
 print(net,ps,ok,vok,flush=True)
 if not all(ok) or not vok:return False
 track(b,net,ps,w,layer)
 if via_end:via(b,net,*ps[-1],vd=1.,dr=.45,grid=False)
 log.append(dict(net=net,points=ps,layer=b.GetLayerName(layer),new_via=via_end));return True
add('/VBUS_RAW',[(4.1,6.85),(4.1,7.7),(4.6,8.2),(7.1882,8.2)],B,True)
add('/VBUS_RAW',[(9.55,7.045),(9.55,7.7),(9.05,8.2),(7.1882,8.2)],B,w=.5)
add('/VBUS_RAW',[(14.45,7.045),(14.45,7.7),(14.95,8.2),(17.2212,8.2)],B,True,w=.5)
add('/VBUS_RAW',[(7.1882,8.2),(17.2212,8.2)],F)
add('/VBUS_FUSED',[(4.1,1.95),(4.1,1.45),(4.6,.95),(5.596,.95),(6.096,1.45),(6.096,3.81)],B,True)
add('/VBUS_FUSED',[(6.096,3.81),(6.096,16.1036)],F,True)
add('/VBUS_FUSED',[(6.096,16.1036),(16.7964,16.1036),(17.2,15.7),(19,15.7)],B)
add('/VBUS_FUSED',[(19.5,7.4),(19.5,7.7),(18.9958,8.2042),(18.4912,8.2042)],B,True)
add('/VBUS_FUSED',[(18.4912,8.2042),(17.2,9.4954),(17.2,15.7),(19,15.7)],F)
k.SaveBoard(str(p),b);update("rear",b);(r/'power_corridors.json').write_text(json.dumps(log,indent=2)+'\n')
