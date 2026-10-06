"""Explicit multi-pad load banks and outward high-current routes, P4 only."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import track,via,F,B
from geometry_guard_P3R1 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_master_load_routes.kicad_pcb'),b);log=[]
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ['6235a75c-8f48-4bf6-9ee7-a352396f1aa8','b0d6230f-24f7-4c47-abf8-66fda99a1584']:b.Delete(t)
def add(net,ps,w,l):
 bad=[(a,z) for a,z in zip(ps,ps[1:]) if not Guard(b,net).line_clear(a,z,l,w)]
 if bad:print('BLOCKED',net,bad,flush=True);log.append(dict(net=net,status='BLOCKED',segments=bad));return False
 track(b,net,ps,w,l);log.append(dict(net=net,points=ps,width_mm=w,layer=l,status='ADDED'));return True
for y in [10.365,11.635,12.905]:add('/PACK_FUSED',[(2.525,y),(1.6,y)],.6,B)
add('/PACK_FUSED',[(1.6,10.365),(1.6,12.905)],1.6,B)
for y in [10.75,11.75,12.75]:
 # Native DRC, including hole-to-hole, is the acceptance check. These vias
 # intentionally join same-net source lands/bank and do not cross the package.
 via(b,'/PACK_FUSED',1.6,y,vd=1,dr=.45,grid=False)
for y in [9.095,10.365,11.635,12.905]:add('/BAT_IN',[(7.475,y),(8.5,y)],.6,B)
add('/BAT_IN',[(8.5,9.095),(8.5,12.1)],1.5,B)
for y in [13.095,14.365,15.635,16.905]:add('/BAT_IN',[(10.525,y),(9.65,y)],.6,B)
add('/BAT_IN',[(9.65,13.095),(9.65,16.905)],1.5,B)
add('/BAT_IN',[(8.5,12.1),(9.65,13.25)],1.5,B)
add('/H_DUMP_D',[(73.4375,45),(74.5,45)],.6,B)
add('/H_DUMP_D',[(74.5,45),(74.5,48.5),(72.5,50.5),(65,50.5),(65,48)],1,B)
add('/+5V_MOTION',[(17.775,20),(14.9,20),(12,20),(10,22),(4.5,22),(4.5,21)],.8,F)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'master_load_routes.json').write_text(json.dumps(log,indent=2)+'\n')
