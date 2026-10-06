"""P3 motion U1 enable corridor and shorter C1 supply approach (one-off stage)."""
import pcbnew as k, json
from layout_P3 import paths,xy,pt,F,B,track,via,setplace
from geometry_guard_P3 import line_clear,via_clear,obstacles
from route_local_P3 import connect
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
k.SaveBoard(str(r/'before_u1_cap_move.kicad_pcb'),b)
# Remove the obsolete long decoupling loop encircling U1's outward pin escape.
ids=['87d8dda3-8556-48f4-b3b8-86296ed4daa0','2865e9a4-4268-4d77-8cbc-3e43f6f7fb4d','94528ed4-e9b5-4e65-a19f-bd85aa85fe79','412663d4-32a9-4a9b-96ef-26e74c2287ed','61cf1152-182b-49e0-b142-e0a62a7c29bd','701b02be-34d3-4f80-b47e-4c3cb4f70b65','eb16e00f-30ce-4397-b283-271d0afe9801','262d1624-5e80-4aae-bcbf-ea8eed9f8599','d40cb170-0163-4dfd-b98d-7569c47124a3','096eb590-d958-4c62-919f-078a4ca2fbe6']
c1pads={q.GetNumber():q for q in fps['C1'].Pads()};oldg=pt(*xy(c1pads['2'].GetPosition()))
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids or (t.GetNetname()=='/GND' and (t.GetStart()==oldg or t.GetEnd()==oldg)):b.Delete(t)
setplace(fps['C1'],31.75,13.5,180,'B')
# Cap VCC enters existing supply corridor in a straight line.
a=xy(c1pads['1'].GetPosition());z=(a[0],11.5)
assert line_clear(b,'/+3V3',a,z,B),('C1 supply blocked',a,z)
track(b,'+3V3',[a,z],.2,B)
# U1 OE's pin-outward escape has deliberate room before its layer transition.
for pos in [(25.2,11.0),(21.4,12.8)]:
 assert via_clear(b,'/S288_OE_N',pos),(pos,[obstacles(b,'/S288_OE_N',pos,l,.8,True) for l in [F,B]])
 via(b,'S288_OE_N',*pos,grid=False)
points=[(26.45,10.75),(25.45,10.75),(25.2,11.0)]
for a,z in zip(points,points[1:]):assert line_clear(b,'/S288_OE_N',a,z,B),(a,z)
track(b,'S288_OE_N',points,.2,B)
log=[]
log.append(connect(b,'/S288_OE_N',(18.55,11.25),(21.4,12.8),[B],[B],(70,35)))
log.append(connect(b,'/S288_OE_N',(21.4,12.8),(25.2,11.0),[F],[F],(70,35)))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'motion_enable_close.json').write_text(json.dumps(log,indent=2)+'\n')
