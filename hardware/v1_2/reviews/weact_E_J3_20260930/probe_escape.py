from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
b=k.LoadBoard(str(HERE/'reports/motion/socket_escape_v4_partial.kicad_pcb'))
for q in [(54.5,y)for y in [10,10.5,11,11.5,12,12.5,12.9,13.3,13.7,14.1]]:
 print(q,{b.GetLayerName(l):obstacles(b,'/FAULT_N',q,l)for l in[k.F_Cu,k.B_Cu]})
print('Candidate horizontal F south of J7')
for y in [12.9,13,13.1,13.2,13.3,13.4]:
 bad=[]
 for i in range(430,546):
  q=(i/10,y);o=obstacles(b,'/FAULT_N',q,k.F_Cu)
  if o:bad.append((q,o))
 print(y,bad[::max(1,len(bad)//5)])
print('candidate vias')
g=Guard(b,'/FAULT_N')
for y in [12.9,13.1,13.3]:
 print(y,[(x/10,y)for x in range(415,546)if g.via_clear((x/10,y))])
