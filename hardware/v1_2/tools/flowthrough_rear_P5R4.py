"""Enforce actual flow-through geometry, including same-net overlap screening.

DRC cannot detect a same-net bypass of a TVS pad. Move D3 north 0.5 mm
so its output via can be downstream, away from the incoming copper.
"""
from review_P5R4 import *
e=Edit('rear')
e.move('D3',(14.3,9.5),0)
e.remove(net='/CC2')
e.add('/CC2',B,[(13.75,7.045),(13.75,8.1),(13.25,8.6),(13.25,9.5)])
e.add('/CC2',B,[(13.25,9.5),(13.25,10.7)])
e.via('/CC2',(13.25,10.7))
e.add('/CC2',F,[(13.25,10.7),(13.25,8.5),(15.6,8.5),(16.35,9.25),(16.6,9.25),(17.05,9.7),(17.05,21.2),(17.55,21.7),(19,21.7)])
# Reconnect the shifted ground pad to the accepted short ground via.
e.remove(net='/GND',predicate=lambda t: not isinstance(t,k.PCB_VIA) and t.GetLayer()==B and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>=15.3 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<11)
e.add('/GND',B,[(15.35,9.5),(15.95,10.1),(15.95,10.7)],.3)
# Keep RAW power north of the relocated diode body.
e.remove(net='/VBUS_RAW',predicate=lambda t: not isinstance(t,k.PCB_VIA) and t.GetLayer()==B and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>=14.4 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<=8.8001)
e.add('/VBUS_RAW',B,[(14.45,7.045),(14.45,8),(14.75,8.3),(16.7,8.3)],.5)
e.add('/VBUS_RAW',B,[(16.7,8.3),(16.7,8.8)],.2)
e.save()
import polish_P5
polish_P5.paths4=paths;polish_P5.polish('rear')
e.b=k.LoadBoard(str(e.p));e.check('rear_true_flowthrough_01')
