from review_P5R5 import *
from close_P5 import clusters
from route_native_P5 import connect

e=Edit('power')
e.remove(ids=['11c71380','24168a3c','2e8426f5','82c8a12c','ba7ec1a0','baf5ae2a','a8d989bf','7930bf61','3dda3f0b','7241dc0d','5e690cc4'])
e.add('/M5_EN',B,[(11.2,31.6),(11.2,32.6912),(6.604,37.2872)],.2)
e.remove(ids=['37ee6280','7a77d4f0','ca8cf7fa','b6e38ad6','5f921bc5','57b63b84','c2cf142a'])
e.add('/M5_EN',B,[(29.89,26),(29.7,26.19),(29.7,27.4)],.2)
e.add('/M5_EN',B,[(30.3,28),(31,28),(31,29.1),(28.1,29.1)],.2)
e.remove(ids=['8808afb3','d47e8402','c5abf386','746bd46a','6f422510','c8684e24','71a8826c','fca801c2','80c14d6c','d4b96127'])
# Remove the abandoned F branches at the now-unused output sample via.
e.remove(net='/+5V_MOTION',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==F and (xy(t.GetStart())==(32.75,27.2)or xy(t.GetEnd())==(32.75,27.2)))
e.add('/WHEEL_ADC',F,[(42.2,37),(44.5,37)],.2)
for t in e.b.GetTracks():
 if t.m_Uuid.AsString().startswith('cd029717'):t.SetStart(pt(19.1008,19.304))
e.remove(ids=['fc94a7b7']);e.save()
net='/CHG_N';cs=clusters(e.b,net);print('CHG clusters',len(cs),flush=True)
if len(cs)>1:
 starts,goals=cs[:2]
 result=connect(e.b,net,next(iter(starts)),next(iter(goals)),[F,B],[F,B],(80,55),step=.1,width=.2,vd=.8,dr=.3,time_limit=50,max_nodes=900000,heuristic_weight=3,start_points=starts,goal_points=goals);print(result,flush=True);e.save()
