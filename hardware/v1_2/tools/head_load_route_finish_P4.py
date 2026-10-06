"""Establish an explicit head-load trunk, separate from control takeoffs."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import xy,setplace,pt,F,B
from body_keepouts_P3R1 import create
from route_local_P4 import connect
from geometry_guard_P3R1 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_head_load_completion.kicad_pcb'),b)
ids={'6bb6e893-a478-4bad-bcb4-2f23f2379a35','8ec98905-6a21-429c-a107-7ba628275e9b','5d72754c-d8eb-49a3-ab2c-b05ff652f448','3382a3de-817a-44ed-a608-180fe951400f','3a2c0be0-8bb4-493b-8957-f6ae35ae9cfc','317e8f03-8c1e-479f-9602-3135088bbbf0','59a7b107-6dad-46ce-a9f0-f0d6345a9ed6','f0ff23c6-c978-4fe7-a9ba-2bd80ef021b8'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.Delete(t)
f=next(f for f in b.GetFootprints() if f.GetReference()=='J9')
oldpads=[(q.GetNetname(),xy(q.GetPosition())) for q in f.Pads()]
for t in b.GetTracks():
 if t.Type()==k.PCB_VIA_T:continue
 for get,put in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
  pos=xy(get())
  if any(t.GetNetname()==n and abs(pos[0]-q[0])<.02 and abs(pos[1]-q[1])<.02 for n,q in oldpads):put(pt(pos[0]-.25,pos[1]))
setplace(f,52.25,49,0,'F');create(b)
from layout_P3R1 import track
ps=[(43.45,31.0625),(43.45,29.625),(42.825,29)]
if all(Guard(b,'/GND').line_clear(a,z,B,.25) for a,z in zip(ps,ps[1:])):track(b,'/GND',ps,.25,B);print('Q31 ground to actual R54 ground added',flush=True)
log=[]
for a,z in [((47,38),(54.75,49)),((54.75,49),(66.8,51.2))]:
 try:
  result=connect(b,'/H_VM',a,z,[F,B],[F,B],(80,55),step=.1,width=1.0,vd=1.2,dr=.7,max_nodes=800000,time_limit=55,heuristic_weight=1.5);log.append(dict(width_mm=1.0,**result))
 except RuntimeError as e:print('LOAD BLOCKED',e,flush=True);log.append(dict(status='BLOCKED',error=str(e)))
 k.SaveBoard(str(p),b)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'head_load_completion.json').write_text(json.dumps(log,indent=2)+'\n')
