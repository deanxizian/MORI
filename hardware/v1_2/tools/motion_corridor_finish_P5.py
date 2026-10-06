"""Straighten remaining carrier paths after ADC group alignment."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
from close_routes_P2 import merge_lines
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_motion_corridor_finish.kicad_pcb'),b)
remove={'7f756e57-e987-449b-8aa9-562ec12b8416','e54eaf4c-4ab9-48c3-a1e2-f538b8662dc0','61e03785-5f38-44c6-a989-a55ff19b53bb','a48e2b44-14ec-48a2-8ee3-832b3de53245','f86f857b-9bf9-4374-99a8-5a8165ebec0d','61831c66-0a93-417a-97eb-7c681eb6e150'}
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA)or t.GetLayer()!=B:continue
 if t.m_Uuid.AsString()in remove or t.GetNetname()=='/LINK_RX' or (t.GetNetname()=='/BAT_ADC'and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>=27.999):b.Delete(t)
routes=[('/ARM_CLK',[(10.25,7.95),(9.91,7.95)]),('/LINK_RX',[(34.1376,7.2136),(35.5346,8.6106),(36.3106,8.6106),(36.95,9.25),(37.45,9.25)]),('/HEAD_RX',[(18.9992,29.1592),(19.3056,28.8528),(20.1184,28.8528),(20.828,28.1432)]),('/BAT_ADC',[(11.125,28),(10.85,28),(10.35,28.5),(10.35,28.85),(11.18,29.68),(11.18,31.47),(12.45,32.74)])]
for net,ps in routes:
 checks=[Guard(b,net).line_clear(a,z,B,.2)for a,z in zip(ps,ps[1:])];print(net,checks,flush=True);assert all(checks)
 track(b,net,ps,.2,B)
merge_lines(b);k.SaveBoard(str(p),b);(r/'carrier_corridor_finish.json').write_text(json.dumps(routes,indent=2)+'\n')
