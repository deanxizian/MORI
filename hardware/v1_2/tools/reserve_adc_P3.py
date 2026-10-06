"""Reserve parallel J10 analog exits before less constrained status lines."""
import json,math,itertools
import pcbnew as k
from layout_P3 import paths,xy,pt,F,B,via,track
from geometry_guard_P3 import Guard,obstacles
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_adc_fanout.kicad_pcb'),b)
remove={'a989d69c-a3cd-4010-b515-40bca39858f9','c7b614ce-65e9-46eb-9017-cd5002fd3c97','690953c4-724a-4019-a556-1a7b3acc740c','c934a932-53df-4146-b529-0e2dd7ab499c','3df594f3-60c6-4d25-9fd6-0bf2e74da2f1'}
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/CHG_N','/FAULT_N'] or t.m_Uuid.AsString() in remove:b.Delete(t)
# Ground jumpers crossing the connector's escape lane are replaced by local plane ties.
remove=set()
for net,x in [('/BAT_ADC',45.625),('/WHEEL_ADC',46.875),('/CURRENT_ADC',48.125)]:
 for n in range(32):
  for uid,nn in obstacles(b,net,(x,30.95+n*.1),F):
   if nn=='/GND':remove.add(uid)
 for l in [F,B]:
  for uid,nn in obstacles(b,net,(x,33.0),l,.8,True):
   if nn=='/GND':remove.add(uid)
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove:b.Delete(t)
log=[]
# All routes leave connector pins downwards. Fixed vias in a single aligned row.
for net,x in [('/BAT_ADC',45.625),('/WHEEL_ADC',46.875),('/CURRENT_ADC',48.125)]:
 guard=Guard(b,net);a=(x,30.95);z=(x,33.0)
 assert guard.via_clear(z),('target via',net,z,[obstacles(b,net,z,l,.8,True) for l in [F,B]])
 assert guard.line_clear(a,z,F),('target escape',net)
 via(b,net,*z,grid=False);track(b,net,[a,z],.2,F);log.append(dict(net=net,target=z))
for row,start in zip(log,[(31.175,23),(34.675,24),(23.8625,21.95)]):
 net=row['net'];guard=Guard(b,net);options=list(itertools.islice(guard.portals(start,B,4),20))
 assert options,('source escape',net)
 # Prefer an outward route and no direct inward travel across a component.
 if net=='/WHEEL_ADC':options=[a for a in options if a[1][0]<start[0]] or options
 _,z,route=options[0];via(b,net,*z,grid=False);track(b,net,route,.2,B);row['source']=z;row['source_route']=route
k.SaveBoard(str(p),b)
for row in log:
 try:row['route']=connect(b,row['net'],row['source'],row['target'],[F],[B],(80,55));k.SaveBoard(str(p),b)
 except RuntimeError as e:row['blocked']=str(e);print(row['blocked'],flush=True)
try:log.append(connect(b,'/W_VM',(34.675,22),(48,20),[B],[F],(80,55)))
except RuntimeError as e:print('W_VM',str(e),flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'adc_fanout.json').write_text(json.dumps(log,indent=2)+'\n')
