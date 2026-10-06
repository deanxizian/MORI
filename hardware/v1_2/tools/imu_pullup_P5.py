import json,math
import pcbnew as k
from layout_P5 import *
from geometry_guard_P5 import Guard
from body_P5 import create
from close_P5 import clusters
name,d,p,r=paths('imu');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
# Remove the old pull-up branches; rotate the actual component, not a drawn label.
old=xy(fs['R2'].GetPosition())
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CS_N':b.Delete(t)
 elif t.GetNetname()=='/+3V3' and not isinstance(t,k.PCB_VIA):
  a,z=xy(t.GetStart()),xy(t.GetEnd())
  if max(a[0],z[0])>16:b.Delete(t)
setplace(fs['R2'],15.9,8.4,270,'F');create(b,'imu')
ps=[(15.9,9.225),(14.45,10.675),(13.2,10.675)];g=Guard(b,'/+3V3')
assert all(g.line_clear(a,z,F) for a,z in zip(ps,ps[1:])),ps
track(b,'/+3V3',ps,.2,F)
# Drop only electrically redundant +3V3 graph edges. Every pad must remain
# in one copper island; no nominal-width or keepout waiver is involved.
removed=[]
for t in sorted([t for t in b.GetTracks() if t.GetNetname()=='/+3V3' and not isinstance(t,k.PCB_VIA)],key=lambda t:t.GetLength(),reverse=True):
 row=(str(t.GetNetname()),xy(t.GetStart()),xy(t.GetEnd()),k.ToMM(t.GetWidth()),t.GetLayer());uid=t.m_Uuid.AsString();b.Remove(t)
 if len(clusters(b,'/+3V3'))==1:removed.append(uid)
 else:b.Add(t)
k.SaveBoard(str(p),b);update('imu',b)
(r/'pullup_rotation.json').write_text(json.dumps(dict(ref='R2',old_xy=old,new_xy=[15.9,8.4],new_angle=270,reason='CS faces the header, 3V3 faces its feed; removes the acute outward-then-fold-back branch.',removed_redundant_supply_edges=removed),indent=2)+'\n')
