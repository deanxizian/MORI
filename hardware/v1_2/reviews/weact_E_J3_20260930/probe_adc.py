from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
b=k.LoadBoard(str(HERE/'reports/motion/R9_lower_partial.kicad_pcb'))
for x in [58.5,59,59.5,60.5]:
 for y in [10,11,12,13,13.5,14,14.5,15,15.5,16,17,18,19,20,21,22,23]:
  o=obstacles(b,'/BAT_ADC_IN',(x,y),k.B_Cu)
  if o:print(x,y,o)
for f in b.GetFootprints():
 if f.GetReference()in ['J5','J3','R9']:print(f.GetReference(),rect(f))
