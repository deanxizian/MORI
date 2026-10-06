"""Compare a 1.5mm resistor move to repeated signal detours."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from close_P5 import clusters
from body_keepouts_P3R1 import rectangle
OUT=HERE/'reports/motion';name,d,p=paths('motion')
b=k.LoadBoard(str(OUT/'R9_lower_partial.kicad_pcb'))
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CAM_TX':b.Delete(t)
base=k.LoadBoard(str(OUT/'socket_escape_v5_partial.kicad_pcb'))
old_chg={t.m_Uuid.AsString()for t in base.GetTracks()if t.GetNetname()=='/CHG_N'}
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CHG_N'and t.m_Uuid.AsString()not in old_chg:b.Delete(t)
class SocketGuard(Guard):
 def clear(self,q,layer,width=.2,is_via=False):
  for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
   if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
  return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b
plans=[]
for net in ['/BAT_ADC_IN','/WHEEL_ADC_IN','/CURRENT_ADC_IN','/CAM_TX','/CHG_N']:
 r.SEARCH_BOUNDS=(37,59,8.6,22) if net.startswith('/CAM_RX') else (.6,69.4,.6,34.4)
 r.GRID_OFFSET=(0,.05)
 cs=clusters(b,net);print(net,'initial islands',len(cs),flush=True)
 assert len(cs)==2,(net,len(cs))
 options=[[(q,l)for q,ls in group.items()for l in ls]for group in cs];options.sort(key=len,reverse=True)
 r.START_OPTIONS=options[0];plans.append(r.plan(net,options[0][0],options[1]))
 assert len(clusters(b,net))==1,net
 dump(OUT/'adc_priority_routes.json',plans);k.SaveBoard(str(OUT/'adc_priority_partial.kicad_pcb'),b)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','adc_priority')
