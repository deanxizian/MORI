"""Bounded rear routing trials, native DRC gate, no source overwrites."""
from review_P5R4 import *
from geometry_guard_P5 import Guard

e = Edit('rear')
e.remove(net='/CC2')
e.remove(ids=['67e2b214','8059831d','0841cb06','9fb81732','f41bad2c','aa977424','776dbf6f'])
e.via('/VBUS_RAW',(16.7,8.3),1,.45)
e.add('/VBUS_RAW',B,[(14.45,8.5),(14.75,8.8),(16.7,8.8),(16.7,8.3)],.5)
e.add('/VBUS_RAW',B,[(16.7,8.8),(16.7,14.85),(16.4,15.15),(16,15.15)],.2)
# Both branches terminate at the protection pad, not the pre-TVS via.
e.add('/CC2', B, [(13.75,7.045),(13.75,8.4),(13.25,8.9),(13.25,10)], .2)
e.add('/CC2', B, [(13.25,10),(12.7,10),(12.7,9.1),(13.1,8.7)], .2)
e.via('/CC2', (13.1,8.7))
e.add('/CC2', F, [(13.1,8.7),(15.3,8.7),(15.8,9.2),(16.55,9.2),(17.05,9.7),(17.05,21.2),(17.55,21.7),(19,21.7)], .2)
e.add('/GND', B, [(9.9,9.85),(8.15,9.85),(8,10)], .3)
for ref, p in [('D3',(15.35,10))]:
    guard = Guard(e.b, '/GND')
    choices=[]
    for dist, v, route in guard.portals(p, B, radius=2, step=.05, vd=.8):
        # Only an outward escape and an actual short lead are eligible.
        if ref=='D2' and v[0]>p[0]-.5: continue
        if ref=='D3' and v[0]<p[0]+.5: continue
        if not all(guard.line_clear(a,b,B,.3) for a,b in zip(route,route[1:])):continue
        choices.append((dist,v,route))
        break
    assert choices, ref
    dist,v,route=choices[0]
    e.via('/GND',v)
    e.add('/GND',B,route,.3)
    print(ref,'ground via',v,'distance',dist)
e.save()
import polish_P5
polish_P5.paths4=paths
polish_P5.polish('rear')
e.b=k.LoadBoard(str(e.p))
e.check('rear_ESD_04')
