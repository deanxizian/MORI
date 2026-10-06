"""Remove superseded dead-end and duplicate segments reported by native DRC."""
import pcbnew as k,math
from layout_P3 import paths,pt,xy,F,B
from geometry_guard_P3 import Guard
from close_routes_P2 import merge_lines,snap_via_ends
_,d,p,r=paths('power');b=k.LoadBoard(str(p));ids=['92b33481-349f-4183-ad83-8f4f45eb5f2d','34f73442-4cf0-4fdb-9c26-94a79f54722a','95746590-88e7-4e62-a9a0-f1a09d29d287','07b39f3d-2c0a-48c3-aca4-cafe87a53b77','ffd030f3-3a76-4237-9f52-2830ae4d2254','e2968561-5f1a-4931-9d3b-e36d76ca4d7e','82f4c3c7-8e27-4b86-9a7a-e49ba6c4d0c7','82f4c3c7-8e27-4b86-9f8a-a72f2b660745','debf18d8-5b47-4aaa-865b-abf693d36d28']
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.Delete(t)
 elif t.m_Uuid.AsString()=='c2ecd949-03a7-4bdf-90bb-3b79a068bb85':
  assert Guard(b,'/BAT_MON').line_clear((29.8,15.8),(29,15.8),B);t.SetEnd(pt(29,15.8))
 elif isinstance(t,k.PCB_VIA) and t.GetNetname()=='/+5V_MOTION' and math.dist(xy(t.GetPosition()),(7.8,21.7))<.1:b.Delete(t)
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
