"""Select direct own-pin connector escapes before signal routing.

Narrow body slots are specific to those terminal positions; existing NETBODY
rules still forbid foreign nets anywhere in the full connector body projection.
"""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from close_P5 import clusters
from body_keepouts_P3R1 import rectangle
OUT=HERE/'reports/motion';name,d,p=paths('motion')
b=k.LoadBoard(str(OUT/'long_socket_screen_source.kicad_pcb'))
remove=set(json.loads((OUT/'long_socket_routes.json').read_text())['removed'])
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove or t.GetNetname() in ['/WHEEL_ADC_IN','/CURRENT_ADC_IN']:
  b.Delete(t);continue
 if t.GetNetname()=='/CHG_N':
  if isinstance(t,k.PCB_VIA):
   if xy(t.GetPosition())==(36.474399,7.0104):b.Delete(t)
  elif t.GetLayer()==k.F_Cu and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<=20.5:b.Delete(t)
track(b,'/+3V3',[(10.7442,7.95),(10.7442,6.65)],.2,k.B_Cu)
via(b,'/+3V3',10.7442,6.65,vd=.8,dr=.3,grid=False)
for z in b.Zones():
 if z.GetZoneName() in ['BODY_J7','BODY_J7_OPPOSITE']:
  for x in [56.5,60.5,62.5]:z.Outline().BooleanSubtract(rectangle([x-.3,9.7,x+.3,12.81]))
 if z.GetZoneName() in ['BODY_J2','BODY_J2_OPPOSITE']:
  z.Outline().BooleanSubtract(rectangle([48.63,2.7,51.3,3.3]))
class SocketGuard(Guard):
 def clear(self,q,layer,width=.2,is_via=False):
  for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
   if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
  return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(5.4,68.5,6.2,28.7)
plans=[]
for net in ['/S288_BUS','/WHEEL_ADC_IN','/CURRENT_ADC_IN','/CHG_N']:
 r.SEARCH_BOUNDS=(25,69.4,.6,17) if net=='/S288_BUS' else (5.4,68.5,6.2,28.7)
 cs=clusters(b,net);print(net,'initial islands',len(cs),flush=True)
 for iteration in range(4):
  cs=clusters(b,net)
  if len(cs)==1:break
  assert len(cs)==2,(net,'unexpected island count',len(cs))
  options=[[(q,l)for q,ls in group.items()for l in ls]for group in cs];options.sort(key=len,reverse=True)
  r.START_OPTIONS=options[0]
  plans.append(r.plan(net,options[0][0],options[1]))
  dump(OUT/'socket_escape_v3_routes.json',{'removed':sorted(remove),'routes':plans})
  k.SaveBoard(str(OUT/'socket_escape_v3_partial.kicad_pcb'),b)
 assert len(clusters(b,net))==1,net
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6')
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','socket_escape_v3')
