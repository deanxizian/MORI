"""Compare a 1.5mm resistor move to repeated signal detours."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from close_P5 import clusters
from body_keepouts_P3R1 import rectangle
OUT=HERE/'reports/motion';name,d,p=paths('motion')
b=k.LoadBoard(str(OUT/'socket_escape_v5_partial.kicad_pcb'))
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/CAM_RX_BUF','/CAM_RX']:b.Delete(t)
f=next(f for f in b.GetFootprints()if f.GetReference()=='R9');f.Move(pt(0,1.5))
for z in b.Zones():
 if z.GetZoneName() in [a+'R9'+c for a in ['BODY_','NETBODY_','VIA_BODY_']for c in ['', '_OPPOSITE']]:z.Move(pt(0,1.5))
# Restore the unused J2 escape modification. Its final route uses the old north slot.
old=k.LoadBoard(str(OUT/'long_socket_screen_source.kicad_pcb'))
for z in list(b.Zones()):
 if z.GetZoneName() in ['BODY_J2','BODY_J2_OPPOSITE']:b.Delete(z)
for z in old.Zones():
 if z.GetZoneName() in ['BODY_J2','BODY_J2_OPPOSITE']:b.Add(z.Duplicate(False))
class SocketGuard(Guard):
 def clear(self,q,layer,width=.2,is_via=False):
  for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
   if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
  return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b
plans=[]
for net in ['/CAM_RX_BUF','/CAM_RX','/CHG_N','/BAT_ADC_IN','/WHEEL_ADC_IN','/CURRENT_ADC_IN']:
 r.SEARCH_BOUNDS=(37,59,8.6,22) if net.startswith('/CAM_RX') else (5.4,68.5,6.2,28.7)
 cs=clusters(b,net);print(net,'initial islands',len(cs),flush=True)
 assert len(cs)==2,(net,len(cs))
 options=[[(q,l)for q,ls in group.items()for l in ls]for group in cs];options.sort(key=len,reverse=True)
 r.START_OPTIONS=options[0];plans.append(r.plan(net,options[0][0],options[1]))
 assert len(clusters(b,net))==1,net
 dump(OUT/'R9_corridor_routes.json',plans);k.SaveBoard(str(OUT/'R9_corridor_partial.kicad_pcb'),b)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','R9_corridor')
