import sys
sys.path.insert(0,'hardware/v1_2/tools')
from layout_P5 import *
from geometry_guard_P5 import Guard
name,d,p,r=paths('imu');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CS_N':b.Delete(t)
pathsCS=[[(13,3.5),(13,6.8),(12,7.8),(10.5,7.8),(10.5,8.6875)],[(13,6.8),(13.775,7.575),(15.9,7.575)]]
g=Guard(b,'/CS_N')
for ps in pathsCS:
 print('CS',[(a,z,g.line_clear(a,z,F)) for a,z in zip(ps,ps[1:])]);assert all(g.line_clear(a,z,F) for a,z in zip(ps,ps[1:]));track(b,'/CS_N',ps,.2,F)
# Rewrite left/right ground fan-in with endpoints at via centres.
left=(7.7978,9.6012);rightold=(12.1158,9.1948);right=(12.1158,9.3472)
for t in list(b.GetTracks()):
 if t.GetNetname()!='/GND':continue
 if isinstance(t,k.PCB_VIA):
  if xy(t.GetPosition())==rightold:t.SetPosition(pt(*right))
 else:
  a,z=xy(t.GetStart()),xy(t.GetEnd())
  if all(7.79<=v[0]<=8.84 and 9.34<=v[1]<=9.86 for v in [a,z]) or all(11.16<=v[0]<=12.12 and 8.84<=v[1]<=9.86 for v in [a,z]):b.Delete(t)
g=Guard(b,'/GND')
for ps in [[(8.8375,9.35),(8.049,9.35),left],[(8.8375,9.85),(8.0466,9.85),left],[(11.1625,8.85),(11.6186,8.85),right],[(11.1625,9.3472),right],[(11.1625,9.85),(11.613,9.85),right]]:
 print('GND',[(a,z,g.line_clear(a,z,F)) for a,z in zip(ps,ps[1:])]);assert all(g.line_clear(a,z,F) for a,z in zip(ps,ps[1:]));track(b,'/GND',ps,.2,F)
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='ccc77b4a-6b24-4bf5-b97f-a88f532a1108':b.Delete(t)
k.SaveBoard(str(p),b)
