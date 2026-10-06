"""Reserve simultaneous, staggered fanout for crowded 0.5 mm logic pins.
This changes only P5, and removes all candidate routes on affected signals.
It never imports copper from an older revision.
"""
import sys,json
import pcbnew as k
from layout_P5 import *
from body_P5 import create
from geometry_guard_P5 import Guard
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
(r/'before_simultaneous_escape.kicad_pcb').write_bytes(p.read_bytes())
nets={'/ARM_Q_N','/S288_TX_BUF','/S288_BUS','/S288_OE_N','/HEAD_OE_N','/HEAD_OE_REQ_N','/S288_OE_REQ_N','/CAM_TX','/LINK_RX','/HEAD_TX'}
boxes=[(25,6,33,12),(17,8.7,24,15),(34.5,8,41,12.5)]
for t in list(b.GetTracks()):
 ps=[xy(t.GetPosition())] if isinstance(t,k.PCB_VIA) else [xy(t.GetStart()),xy(t.GetEnd())]
 if t.GetNetname() in nets or (t.GetNetname() in ['/GND','/+3V3'] and any(any(a<=x<=c and z<=y<=w for x,y in ps) for a,z,c,w in boxes)):
  b.Delete(t)
setplace(fs['R4'],17,7.5,90,'B')
setplace(fs['R1'],31,6.75,90,'B')
setplace(fs['C1'],32.0,11.75,90,'B')
create(b,'motion')
log=[]
def add(ref,pin,points,newvia=True):
 f=fs[ref];q=next(q for q in f.Pads() if q.GetNumber()==pin);net=q.GetNetname();a=xy(q.GetPosition());ps=[a]+points;g=Guard(b,net)
 checks=[g.line_clear(u,v,B) for u,v in zip(ps,ps[1:])]
 if not all(checks) or (newvia and not g.via_clear(ps[-1])):
  print('BLOCKED',ref,pin,net,ps,checks,'via',g.via_clear(ps[-1]),flush=True);return False
 track(b,net,ps,.2,B)
 if newvia:via(b,net,*ps[-1],grid=False)
 log.append(dict(ref=ref,pin=pin,net=net,points=ps,via=newvia));return True
# Pin centre landing coordinates stay exact; grid-aligned vias are beyond body.
add('U3','2',[(19.25,14.5),(20.32,15.57),(20.32,15.6972)])
add('U3','6',[(18.75,8.4),(18.7452,8.3952),(18.7452,8.3058)])
add('U3','3',[(18.75,14.9352),(18.7452,14.94)],False)
# Place this via exactly at the end of a straight landing, avoiding a small jog.
# Replace sub-grid endpoints during the final route simplification pass.
add('U3','7',[(19.25,9.0),(19.95,8.3),(20.7264,8.3),(20.7264,8.3058)])
add('U3','1',[(19.75,13.6),(20.35,14.2),(21.1074,14.2),(21.1074,14.1986)])
add('U3','4',[(18.25,13.6),(17.5514,14.2986)])
add('U3','8',[(20.1,9.95),(20.4,9.65),(20.7264,9.65),(20.7264,9.652)])
# U1 output/return fanout is reserved together; old GND via no longer caps TX.
add('U1','6',[(30.0,8.75),(31,7.75),(31,7.575)],False)
add('U1','7',[(31.5976,9.25),(31.5976,9.2456)])
add('U1','8',[(30.2,9.75),(30.7086,10.2586),(30.7086,10.668)])
# VCC gets a real plane via before the two surrounding UART signals.
add('U4','3',[(35.7632,9.75),(35.7632,9.7536)])
add('U4','4',[(36.95,9.25),(36.3,8.6),(35.7632,8.6),(35.7632,8.6106)])
add('U4','2',[(36.95,10.25),(36.1696,11.0304),(36.1696,11.0744)])
add('U4','1',[(37.2,10.75),(36.957,10.993),(36.957,12.3698)])
k.SaveBoard(str(p),b);update('motion',b)
(r/'simultaneous_escape.json').write_text(json.dumps(dict(rerouted_nets=sorted(nets),routes=log),indent=2)+'\n')
