"""Short, explicit VDD/C1/C2/GND6 loop outside the TDK body keepout."""
from review_P5R4 import *

e=Edit('imu')
e.move('C1',(12.5,11.7),-90)
e.move('C2',(12.5,14.25),180)
e.remove(net='/+3V3')
e.remove(ids=['3100f3eb','eb333678'])
# Preserve C3/5/6 and the sensor-side MISO resistor.
e.add('/+3V3',F,[(3,3.5),(3,7.8),(7.7,12.5),(8.225,12.5)])
e.add('/+3V3',F,[(9.5,10.5125),(9.5,11.05),(8.225,12.325),(8.225,12.5)])
# U1.8 escapes outward before entering the cap pad; no body crossings.
e.add('/+3V3',F,[(11.1625,10.35),(11.65,10.35),(12.225,10.925),(12.5,10.925)])
e.add('/+3V3',F,[(12.5,10.925),(14.1,10.925)])
e.add('/+3V3',F,[(14.1,10.925),(14.6,10.925),(15.9,9.625),(15.9,9.225)])
# Bring the supply around the capacitors' outside, not under their bodies.
e.add('/+3V3',F,[(8.225,12.5),(8.225,13.7),(9.625,15.1),(13.6,15.1),(14.1,14.6),(14.1,14.25),(13.275,14.25)])
e.add('/+3V3',F,[(14.1,14.25),(14.1,10.925)])
e.add('/GND',F,[(12.5,12.475),(11.1,12.475),(10.668,12.043),(10.668,11.5824)],.2)
e.add('/GND',F,[(11.725,14.25),(11.725,13.25),(12.5,12.475)],.25)
e.remove(ids=['31b09718','790f1c74'])
e.add('/DRDY',B,[(10.3632,12.2936),(11.2,13.1304),(13.1,13.1304),(14,12.2304),(14,10.485599),(14.985999,9.4996)])
e.save()
import polish_P5
polish_P5.paths4=paths
polish_P5.polish('imu')
e.b=k.LoadBoard(str(e.p))
e.check('imu_VDD_03')
