from review_P5R3 import *
e=Edit('power')
e.remove(ids=['eb1458e7'])
e.remove(net='/WHEEL_ADC',predicate=lambda t:not isinstance(t,k.PCB_VIA)and xy(t.GetStart())in[(44.675,21),(44.675,22.0642)])
e.add('/WHEEL_ADC',F,[(41.9608,20.421599),(42.5,20.421599),(45.211999,23.133598),(45.211999,23.6728)],.2)
e.add('/WHEEL_ADC',F,[(44.675,21),(44.675,21.8),(44.276701,22.198299)],.2)
e.add('/GND',F,[(41.825,22),(42.9,22)],.2);e.via('/GND',(42.9,22))
e.save()
