from update_native_P5R7 import *
from geometry_guard_P5 import Guard
b=k.LoadBoard(str(HERE/'reports/motion/compact_communications_start.kicad_pcb'))
for t in list(b.GetTracks()):
 if t.GetNetname()=='/FAULT_N'and isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==(36.2,13):b.Delete(t)
g=Guard(b,'/FAULT_N')
for y in [12.6,12.7,12.8,12.9,13,13.1,13.2,13.3,13.4]:print(y,[(x/10,y)for x in range(348,368)if g.via_clear((x/10,y))])
