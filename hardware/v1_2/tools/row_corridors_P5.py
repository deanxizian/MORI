"""Deliberate row routing for the P5 connector placement, native checks follow."""
import sys,json
import pcbnew as k
from layout_P5 import *
from geometry_guard_P5 import Guard
from close_P5 import connected
kind='motion';name,d,p,r=paths(kind);b=k.LoadBoard(str(p));connected(b)
k.SaveBoard(str(r/'before_row_corridors.kicad_pcb'),b)
removed=[]
for t in list(b.GetTracks()):
 n=t.GetNetname()
 if (n=='/CAM_TX' and not isinstance(t,k.PCB_VIA) and t.GetLayer()==F) or (n== '/+5V_MOTION' and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])>45.5) or t.m_Uuid.AsString()=='7902da24-fcb3-4055-ae62-60ee6325b7ab':
  removed.append(t.m_Uuid.AsString());b.Delete(t)
log=[]
def add(n,ps,w,l):
 g=Guard(b,n);ok=all(g.line_clear(a,z,l,w) for a,z in zip(ps,ps[1:]));print(n,ps,ok,flush=True)
 if not ok:return False
 track(b,n,ps,w,l);log.append(dict(net=n,points=ps,width=w,layer=l));return True
add('/HEAD_BUS',[(62,18),(62,14.8),(61.5,14.3),(48.5,14.3)],.2,F)
add('/CAM_TX',[(52.5,18),(52.5,15.5),(52,15),(48.5,15)],.2,F)
if Guard(b,'/+5V_MOTION').via_clear((57,6.25)):
 via(b,'/+5V_MOTION',(57,6.25),.8,.3)
 add('/+5V_MOTION',[(58.5,3),(58.5,6.25),(57,6.25)],.5,F)
 add('/+5V_MOTION',[(57,6.25),(45.45,6.25),(45.2,6),(44.7,6)],.5,B)
add('/CHG_N',[(56.5,10),(56.5,7.7),(55.75,6.95),(48.5,6.95)],.2,B)
k.SaveBoard(str(p),b);(r/'row_corridors.json').write_text(json.dumps(dict(removed=removed,routes=log),indent=2)+'\n')
