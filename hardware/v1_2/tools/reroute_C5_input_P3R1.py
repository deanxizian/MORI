"""Move the upstream C5 VIN feed to B.Cu so the SW bootstrap tap stays short.

Local VIN decoupling at U70/C71 is retained. The new input feed is .8 mm with
1/.45 mm vias. Only obstructing .2 mm output-sense copper is displaced.
"""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,F,B
from geometry_guard_P3R1 import obstacles,Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));ts={t.m_Uuid.AsString():t for t in b.GetTracks()};bad=set()
jobs=[(F,[(29.1,35.6),(31,37.5)]),(B,[(31,37.5),(31,39.5),(29.1,41.4)])]
for l,ps in jobs:
 for a,z in zip(ps,ps[1:]):
  for i in range(151):
   pos=(a[0]+(z[0]-a[0])*i/150,a[1]+(z[1]-a[1])*i/150)
   for uid,net in obstacles(b,'/C5_VIN',pos,l,.8):bad.add(uid)
for pos in [(31,37.5)]:
 for l in [F,B]:
  for uid,net in obstacles(b,'/C5_VIN',pos,l,1,True):bad.add(uid)
for uid in bad:
 t=ts[uid];assert t.GetNetname()=='/+5V_CAM' and ((isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth(F))<.9) or (not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<=.2)),uid
for uid in bad:b.Delete(ts[uid])
b.Delete(ts['df6ba797-d37f-44c1-aa6a-3185b072b5b3'])
for l,ps in jobs:
 assert all(Guard(b,'/C5_VIN').line_clear(a,z,l,.8) for a,z in zip(ps,ps[1:])),ps
 track(b,'/C5_VIN',ps,.8,l)
for pos in [(31,37.5)]:
 assert Guard(b,'/C5_VIN').via_clear(pos,1),pos
 via(b,'/C5_VIN',*pos,vd=1,dr=.45,grid=False)
# Displace the old long GND escape; reconnect U70.1 locally to its ground plane.
b.Delete(ts['5faad4e4-a4ba-4d2c-8776-2aeb6891026b'])
ps=[(23.225,40),(24.9,40),(25.4,39.5),(30.225,39.5)]

for a,z in zip(ps,ps[1:]):
 bad_sw=set()
 for i in range(151):
  bad_sw.update(obstacles(b,'/C5_SW',(a[0]+(z[0]-a[0])*i/150,a[1]+(z[1]-a[1])*i/150),F,.2))
 assert not bad_sw,(a,z,bad_sw)
track(b,'/C5_SW',ps,.2,F)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'C5_input_and_bootstrap.json').write_text(json.dumps(dict(input_width_mm=.8,input_vias_mm=[1,.45],input_routes=jobs,SW_bootstrap_F_Cu=ps,SW_bootstrap_vias=0,displaced_feedback_uuids=sorted(bad),thermal_and_switch_waveform='NOT_TESTED'),indent=2)+'\n')
print('C5 input rerouted; SW bootstrap tap F.Cu only',flush=True)
