"""Compare the TVS horizontal orientation to remove its wraparound branch."""
from review_P5R4 import *
e=Edit('rear')
e.move('D1',(3.9,17.7),180)
e.remove(net='/VBUS_FUSED',predicate=lambda t: t.GetLayer()==B and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])<6.2 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])>16.2)
e.remove(net='/GND',predicate=lambda t: (isinstance(t,k.PCB_VIA) and (xy(t.GetPosition()) in [(2,17.5),(4.3,15.1)])) or (not isinstance(t,k.PCB_VIA) and xy(t.GetStart())==(4.3,16.3)))
e.add('/VBUS_FUSED',B,[(6.096,16.1036),(5.65,16.5496),(5.65,17.7),(5.3,17.7)],.6)
e.add('/VBUS_FUSED',B,[(5.65,17.7),(5.65,21.05),(5.175,21.525),(4.3,21.525)],.3)
e.remove(net='/GND',predicate=lambda t:not isinstance(t,k.PCB_VIA) and t.GetLayer()==B and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>=17 and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<=3.1)
e.add('/GND',B,[(2.5,17.7),(1.8,17.7),(1.8,18.3),(2.5,19),(3,19)],.5)
e.save()
import polish_P5
polish_P5.paths4=paths;polish_P5.polish('rear')
e.b=k.LoadBoard(str(e.p));e.check('rear_TVS_rotation_02')
