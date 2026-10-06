from pathlib import Path
exec((Path(__file__).parent/'open_R9_wide.py').read_text().split('class SocketGuard')[0])
from geometry_guard_P5 import obstacles
net='/CHG_N';g=Guard(b,net)
for y in [13.5,13.6,13.7,13.8,14,14.2,14.4]:
 print('via',y,[(x/10,y)for x in range(300,531)if g.via_clear((x/10,y))][::3])
for q in [(32.7,14),(33,14),(33.5,13.75),(39,13.75),(41.5,13.75),(47,13.75),(52.5,13.75)]:
 print(q,{b.GetLayerName(l):obstacles(b,net,q,l,.8,True)for l in [k.F_Cu,k.B_Cu]})
k.SaveBoard(str(OUT/'R9_wide_start.kicad_pcb'),b)
