import pcbnew as k,json,math,itertools
from layout_P3 import paths,xy,pt,F,B,track,via,setplace
from geometry_guard_P3 import Guard
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};oldc=[pt(30,12.775),pt(30,11.225)];ids=['18c73421-2b77-4a84-9d93-52c7353ef52a','b7385703-f498-4417-a446-9d3238967df1','de691c56-a948-46d8-81b0-1f2b1b75ea93']
# Free the capacitor courtyard while preserving the already routed gate-control package.
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.Delete(t)
 elif not isinstance(t,k.PCB_VIA) and (t.GetStart() in oldc or t.GetEnd() in oldc):b.Delete(t)
setplace(fps['C2'],30.5,9,90,'B')
# Raise R11 clear of D10; only its own short pin necks change.
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA) or t.GetLayer()!=B:continue
 a,z=xy(t.GetStart()),xy(t.GetEnd())
 if t.GetNetname()=='/W_GATE' and min(a[1],z[1])>=10.49 and max(a[1],z[1])<11.6 and max(a[0],z[0])<42.8:b.Delete(t)
 elif t.GetNetname()=='/W_GATE_LOW' and min(a[0],z[0])>44 and max(a[1],z[1])<11.6:b.Delete(t)
setplace(fps['R11'],43.5,10.5,0,'B')
# Native shapes, including full actual pad extent, validate new copper separations.
for ref in ['C2','R11']:
 for pad in fps[ref].Pads():
  shp=pad.GetEffectiveShape(B)
  for other in fps.values():
   if other==fps[ref]:continue
   for q in other.Pads():
    if q.IsOnLayer(B) and q.GetNetCode()!=pad.GetNetCode():assert not shp.Collide(q.GetEffectiveShape(B),k.FromMM(.201)),(ref,pad.GetNumber(),other.GetReference(),q.GetNumber())
for net,points in [('/W_GATE',[(42.675,10.5),(42.1,10.5)]),('/W_GATE_LOW',[(44.325,10.5),(44.725,10.5),(45.325,11.1)])]:
 g=Guard(b,net);assert all(g.line_clear(a,z,B) for a,z in zip(points,points[1:]));track(b,net,points,.2,B)
# Restore the actual cross-layer output connection; discard only its unused side branch.
assert Guard(b,'/+5V_MOTION').via_clear((7.8,21.7));via(b,'+5V_MOTION',7.8,21.7,grid=False)
for t in b.GetTracks():
 if t.m_Uuid.AsString()=='baa47bfb-33c2-4fb0-873b-3c7b83490e26':t.SetStart(pt(76.4,45))
 if t.m_Uuid.AsString()=='05a86197-4f1a-4c98-90fc-ae962f768a0e':t.SetEnd(pt(60.65,19.35))
k.SaveBoard(str(p),b)
connect(b,'/BAT_MON',(30.5,9.775),(29,13.775),[B],[B],(80,55),step=.025)
a=(30.5,8.225);options=list(itertools.islice(Guard(b,'/GND').portals(a,B,3),1))
if options:
 _,v,route=options[0];via(b,'GND',*v,grid=False);track(b,'GND',route,.2,B)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
