"""Separate the raw sense branch from the CC-protector ground return."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import xy,track,B,F
from route_local_P4 import connect
from geometry_guard_P3R1 import Guard
_,d,p,r=paths('rear');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_rear_return.kicad_pcb'),b)
for t in list(b.GetTracks()):
 if (t.GetNetname()=='/VBUS_RAW' and t.Type()!=k.PCB_VIA_T and k.ToMM(t.GetWidth())<.3) or t.m_Uuid.AsString() in ['4f896d7e-ea8f-46a4-891e-deacaec7ef51','b265b4c0-00b5-4590-b86b-b5cb69c89e5b','ffb3bca9-bc49-4b4c-aac8-a5505aa7a4ea']:b.Delete(t)
log=[]
for net,a,z,al,zl,w in [('/GND',(10.75,11.55),(13.75,11.55),[B],[B],.25),('/VBUS_RAW',(8,23),(9.55,8.4),[F,B],[F,B],.2)]:
 try:log.append(connect(b,net,a,z,al,zl,(24,25),width=w,step=.05,vd=.8,dr=.3,time_limit=35))
 except RuntimeError as e:print(e)
# Fused positive exits PH5 to the outside of PH4, leaving the latter's body clear.
jobs=[(16,23),(18,23),(21.1,19.9),(21.1,18.1)]
if all(Guard(b,'/VBUS_FUSED').line_clear(a,z,F,.6) for a,z in zip(jobs,jobs[1:])):track(b,'/VBUS_FUSED',jobs,.6,F)
else:print('FUSED manual corridor blocked')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'return_corridor.json').write_text(json.dumps(log,indent=2)+'\n')
