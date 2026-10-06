"""Relocate TVS/cap to the protected feed, preserve mounted interfaces."""
from review_P5R4 import *
e=Edit('rear')
e.move('D1',(4.3,17.7),90)
e.move('C1',(4.3,22.3),-90)
e.remove(net='/VBUS_FUSED')
e.add('/VBUS_FUSED',B,[(4.099999,1.95),(4.099999,.95),(4.6,.95),(6.6,2.95),(6.6,3.81),(7.0104,3.81)],.6)
e.via('/VBUS_FUSED',(7.0104,3.81),1,.45)
e.add('/VBUS_FUSED',F,[(7.0104,3.81),(6.596,3.81),(6.096,4.31),(6.096,16.1036)],.6)
e.via('/VBUS_FUSED',(6.096,16.1036),1,.45)
e.add('/VBUS_FUSED',B,[(6.096,16.1036),(16.7964,16.1036),(17.2,15.7),(19,15.7)],.6)
e.add('/VBUS_FUSED',B,[(6.096,16.1036),(5.6,16.5996),(5.6,19.2),(5.3,19.5),(4.3,19.5),(4.3,19.1)],.6)
e.add('/VBUS_FUSED',B,[(4.3,19.5),(4.3,21.525)],.3)
e.add('/GND',B,[(4.3,23.075),(5.4,23.075)],.3)
e.via('/GND',(5.4,23.075),.8,.3)
e.add('/GND',B,[(4.3,16.3),(4.3,15.1)],.5)
e.via('/GND',(4.3,15.1),.8,.3)
# CC1 avoids the relocated TVS and the existing mounting seats.
e.remove(ids=['022f29f3','7dee163b','9c8680a2','e5f08458','184b911f','43f93ba3','8844cffe'])
e.add('/CC1',B,[(11.684,10.9728),(7.112,10.9728),(1.2,16.8848),(1.2,23),(2.4,24.2),(16.9,24.2),(17.4752,23.6248),(17.4752,20.32)])
e.save()
import polish_P5
polish_P5.paths4=paths
polish_P5.polish('rear')
e.b=k.LoadBoard(str(e.p))
e.check('rear_power_04')
