from review_P5R5 import *
from buck_relayout_P5R5 import area

e=Edit('power')
e.remove(ids=['0ac6d8d5','7d76d6bd','cdddcb88'])
# Replace this local F ground corridor; preserve its end-to-end topology.
e.remove(net='/GND',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==F and xy(t.GetStart())==(22.45,39.225)and xy(t.GetEnd())==(21.5,39.225))
e.add('/GND',F,[(22.45,39.225),(21.3,39.225),(21.3,40.5),(20.4,41.4),(20.4,41.6)],.6);e.via('/GND',(21.3,40.5))
e.remove(net='/C5_EN');e.add('/C5_EN',F,[(27.6,40),(28.5,40),(28.5,38.3),(28.15,37.95)],.2);e.via('/C5_EN',(28.15,37.95))
e.remove(net='/GND',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.In1_Cu and 37<xy(t.GetStart())[1]<44)
e.add('/GND',k.In1_Cu,[(31.8,43.5),(29,43.5),(29,37.2),(25.4,37.2),(24.9,37.7)],.2)
for z in list(e.b.Zones()):
 if z.GetZoneName()=='P5R5_QUIET_70_Ireturn':e.b.Delete(z)
area(e,'P5R5_QUIET_70_Ireturn',k.In1_Cu,[(24.3,37.1),(25.0,36.8),(29.4,36.8),(29.4,43.1),(32.4,43.1),(32.4,43.9),(28.6,43.9),(28.6,37.6),(25.55,37.6),(24.9,38.25),(24.3,38.25)])
# A redundant via on the CAM output was left unused by the feedback route.
e.remove(ids=['2d9adc97'])
# Native search snapped this endpoint near, but not to, its explicit via.
for t in e.b.GetTracks():
 if t.m_Uuid.AsString().startswith('02b956e3'):t.SetStart(pt(30.5,27.2))
e.save()
