import pcbnew as k
from layout_P3 import paths,track,via,xy,F
from close_routes_P2 import merge_lines,snap_via_ends
name,d,p,r=paths('imu');b=k.LoadBoard(str(p))
v=via(b,'GND',10.795,11.125)
track(b,'GND',[(9.875,10.9125),(10.5825,10.9125),v],.2,F)
track(b,'GND',[(12.0375,9.25),(12.0375,8.2),(13,8.2)],.2,F)
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
