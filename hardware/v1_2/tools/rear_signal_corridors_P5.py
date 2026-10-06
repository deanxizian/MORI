"""Reserve the return and CC/sense lanes outside the fixed switch body."""
from layout_P5 import *
from body_P5 import create
from geometry_guard_P5 import Guard
n,d,p,r=paths('rear');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
(r/'before_signal_corridors.kicad_pcb').write_bytes(p.read_bytes())
setplace(fs['J3'],8.45,19.5,0,'F');create(b,'rear')
for t in list(b.GetTracks()):
 if t.GetNetname()=='/MASTER_RETURN' or (t.GetNetname()=='/VBUS_RAW' and not isinstance(t,k.PCB_VIA) and t.GetLayer()==F):b.Delete(t)
log=[]
def add(net,ps,l,w=.2,vd=None):
 g=Guard(b,net);cc=[g.line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])];ok=not vd or g.via_clear(ps[-1],vd)
 print(net,ps,cc,'via',ok,flush=True)
 if not all(cc) or not ok:return False
 track(b,net,ps,w,l)
 if vd:via(b,net,*ps[-1],vd=vd,dr=.3 if vd==.8 else .45,grid=False)
 log.append(dict(net=net,points=ps,layer=b.GetLayerName(l),width=w,new_via=bool(vd)));return True
add('/VBUS_RAW',[(7.1882,9),(7.1882,8.3),(7.6882,7.8),(16.2,7.8),(16.7,8.3),(16.7,9)],F,.6)
add('/MASTER_RETURN',[(9.5,10.1),(8.1026,10.1),(8.1026,10.1092)],F,vd=.8)
add('/MASTER_RETURN',[(8.1026,10.1092),(7.7136,10.1092),(7.2136,10.6092),(7.2136,15.2146)],B,vd=.8)
add('/MASTER_RETURN',[(7.2136,15.2146),(7.2136,15.9),(8.45,17.1364),(8.45,19.5)],F)
k.SaveBoard(str(p),b);update('rear',b);(r/'signal_corridors.json').write_text(json.dumps(dict(routes=log,raw_branch='J2.5 presence sense ONLY; electrical_interfaces.json says not charge current. Its branch uses 0.2 mm; USB-to-F1 charging copper remains 0.5/0.6 mm.'),indent=2)+'\n')
