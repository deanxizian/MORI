import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from close_P5 import clusters
OUT=HERE/'reports/motion';name,d,p=paths('motion')
b=k.LoadBoard(str(OUT/'long_socket_screen_source.kicad_pcb'))
remove=set(json.loads((OUT/'long_socket_routes.json').read_text())['removed'])
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove or t.GetNetname() in ['/WHEEL_ADC_IN','/CURRENT_ADC_IN','/CHG_N']: b.Delete(t)
track(b,'/+3V3',[(10.7442,7.95),(10.7442,6.65)],.2,k.B_Cu)
via(b,'/+3V3',10.7442,6.65,vd=.8,dr=.3,grid=False)
class SocketGuard(Guard):
 def clear(self,q,layer,width=.2,is_via=False):
  for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
   if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
  return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(30,55,.6,15)
cs=clusters(b,'/S288_BUS');r.START_OPTIONS=[(q,l)for q,ls in cs[0].items()for l in ls]
ends=[(q,l)for q,ls in cs[1].items()for l in ls]
result=r.plan('/S288_BUS',r.START_OPTIONS[0],ends)
k.SaveBoard(str(OUT/'compact_after_S288.kicad_pcb'),b)
dump(OUT/'compact_after_S288.json',result)
