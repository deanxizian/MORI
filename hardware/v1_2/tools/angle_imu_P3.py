import pcbnew as k
from layout_P3 import paths,pt,track,F
from close_routes_P2 import merge_lines
_,_,p,_=paths('imu');b=k.LoadBoard(str(p))
for t in b.GetTracks():
 if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='/GND' and t.GetStart()==pt(5.7,9.15) and t.GetEnd()==pt(6.3,8.55):t.SetEnd(pt(6.3,9.15))
track(b,'GND',[(6.3,8.55),(6.3,9.15)],.2,F)
merge_lines(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
