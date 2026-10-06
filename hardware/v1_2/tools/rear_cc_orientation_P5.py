"""Rotate both CC protection diodes to leave a continuous signal corridor
above the switch; keep the TVS on the same-side protected power branch."""
from layout_P5 import *
from body_P5 import create
from geometry_guard_P5 import Guard
n,d,p,r=paths('rear');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
(r/'before_cc_orientation.kicad_pcb').write_bytes(p.read_bytes())
for t in list(b.GetTracks()):
 net=str(t.GetNetname());isv=isinstance(t,k.PCB_VIA)
 if net in ['/CC1','/CC2','/MASTER_RETURN'] or (net=='/VBUS_RAW' and ((isv and k.ToMM(t.GetWidth(F))<.9) or (not isv and k.ToMM(t.GetWidth())<.3))) or (net=='/VBUS_FUSED' and ((isv and xy(t.GetPosition())[0]>15) or (not isv and t.GetLayer()==F and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])>15))):b.Delete(t)
for ref,x,ang in [('D2',10.4,180),('D3',14.1,0)]:setplace(fs[ref],x,9.85,ang,'B')
create(b,'rear');log=[]
def add(net,ps,l,w=.2,v=False):
 g=Guard(b,net);cc=[g.line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])];ok=not v or g.via_clear(ps[-1],.8)
 print(net,ps,cc,ok,flush=True)
 if not all(cc) or not ok:return False
 track(b,net,ps,w,l)
 if v:via(b,net,*ps[-1],grid=False)
 log.append(dict(net=net,points=ps,width=w,layer=b.GetLayerName(l),via=v));return True
add('/VBUS_FUSED',[(19.5,7.4),(19.5,7.9),(17.32,10.08),(17.32,15.2),(17.82,15.7),(19,15.7)],B,.6)
add('/MASTER_RETURN',[(9.5,10.1),(7.3,10.1),(6.8,10.6),(6.8,14.95),(7.3,15.45),(7.3,16.3),(8.45,17.45),(8.45,19.5)],F)
add('/CC1',[(10.75,7.045),(10.75,8.55),(11.45,9.25),(11.45,9.85)],B)
add('/CC2',[(13.75,7.045),(13.75,8.55),(13.05,9.25),(13.05,9.85)],B)
add('/CC2',[(13.05,9.85),(13.05,10.35),(13.55,10.85),(16.2,10.85),(16.7,11.35),(16.7,14.6692),(16.256,15.1132)],B,v=True)
add('/CC2',[(16.256,15.1132),(16.256,16.05),(16.8,16.594),(16.8,21.2),(17.3,21.7),(19,21.7)],F)
k.SaveBoard(str(p),b);update('rear',b);(r/'cc_orientation.json').write_text(json.dumps(log,indent=2)+'\n')
