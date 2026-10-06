"""Re-space the IMU signal corridor, then route from actual pad identities."""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,pt,xy,setplace,track,via
from body_keepouts_P3R1 import create
from route_local_P3R1 import connect
from geometry_guard_P3R1 import Guard
from close_routes_P2 import merge_lines
name,d,p,r=paths('imu');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):b.Delete(t)
# Increase the header-to-IC channel. Keep the ICM axes and both mounting holes.
setplace(fps['U1'],9.875,9.5,0)
setplace(fps['C1'],13,9.475,90)
for z in b.Zones():
    if z.GetIsRuleArea() and z.GetZoneName().startswith('TDK_AN000393_under_IMU_'):
        box=z.GetBoundingBox();cx=k.ToMM(box.GetX()+box.GetRight())/2;cy=k.ToMM(box.GetY()+box.GetBottom())/2
        z.Move(pt(9.875-cx,9.5-cy))
# CS pullup now faces the signal towards the IC, not the lower board edge.
setplace(fps['R2'],6.5,13,270)
zones=create(b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
ports={key:xy(pad.GetPosition()) for key,pad in pads.items()}
def put(net,points,layer=k.F_Cu):
    g=Guard(b,net)
    assert all(g.line_clear(a,z,layer,.2) for a,z in zip(points,points[1:])),(net,points)
    track(b,net,points,.2,layer)
def stitch(net,pos):
    assert Guard(b,net).via_clear(pos),(net,pos)
    via(b,net,*pos,grid=False)
# Reserve every IC/header escape before any route can trap a later pin.
for key,pad in pads.items():
    ref,number=key;a=xy(pad.GetPosition());z=None
    if ref=='J1' and number.isdigit():z=(a[0],6.3 if number=='5' else 6.55)
    if ref=='U1':
        n=int(number)
        if n in [12,13,14]:z=(a[0],7.7)
        elif n in [1,2,3,4]:z=(7.8,a[1])
        elif n in [5,6,7]:z=(a[0],11.2)
        else:z=(11.9,a[1])
    if z:put(pad.GetNetname(),[a,z]);ports[key]=z
put('/GND',[(7.8,9.25),(7.8,9.75)])
put('/GND',[(11.9,8.75),(11.9,9.75)])
put('/GND',[(9.875,11.2),(10.775,11.2),(10.925,11.35)])
for pos in [(7.8,9.5),(11.9,9.25),(10.925,11.35)]:stitch('/GND',pos)
for key in [('J1','2'),('J1','8')]:
    a=ports[key];z=(a[0],6.95);put('/GND',[a,z]);stitch('/GND',z)
put('/MOSI',[ports['J1','4'],ports['U1','14']])
# One explicit layer crossover preserves the neighbouring CS and MOSI exits.
put('/SCK',[ports['J1','3'],(8.125,6.95)])
stitch('/SCK',(8.125,6.95));stitch('/SCK',(10.15,6.95))
put('/SCK',[(8.125,6.95),(10.15,6.95)],k.B_Cu)
put('/SCK',[(10.15,6.95),(9.875,7.225),ports['U1','13']])
put('/MISO',[ports['J1','5'],(10.625,6.325),(11.3,7.0)])
stitch('/MISO',(11.3,7.0));stitch('/MISO',(4.275,8.25))
put('/MISO',[(11.3,7.0),(11.3,7.25),(10.8,7.75),(4.775,7.75),(4.275,8.25)],k.B_Cu)
put('/MISO',[(4.275,8.25),ports['R1','2']])
# Keep both small decoupling loops ahead of unrelated SPI wiring.
put('/+3V3',[ports['U1','5'],(9.375,11.55),(9.775,11.95),ports['C3','1']])
put('/+3V3',[ports['U1','8'],ports['C1','1']])
put('/+3V3',[ports['C1','1'],(13,11.0),(13.275,11.275),ports['C2','1'],(13.275,14.2),(6.5,14.2),ports['R2','2']])
put('/+3V3',[ports['C3','1'],(9.775,14.2)])
put('/CS_N',[ports['R2','1'],(6.5,11.4)]);ports['R2','1']=(6.5,11.4)
jobs=[(('J1','1'),('R2','2')),(('J1','6'),('U1','12')),(('R1','1'),('U1','1')),
      (('J1','7'),('U1','4')),(('R2','1'),('U1','12'))]
log=[]
for a,z in jobs:
    pa,pz=pads[a],pads[z];net=pa.GetNetname();assert net==pz.GetNetname(),(a,z)
    try:out=connect(b,net,ports[a],ports[z],[k.F_Cu],[k.F_Cu],(20,16),step=.05);log.append(dict(pins=[a,z],status='ROUTED',**out))
    except RuntimeError as e:log.append(dict(pins=[a,z],status='BLOCKED',reason=str(e)));print('BLOCKED',a,z,str(e),flush=True)
    k.SaveBoard(str(p),b)
(r/'imu_signal_routes.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
merge_lines(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
print('IMU corridor spacing and signal routes saved; ground/native closure required')
