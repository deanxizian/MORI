"""Give the logic-power connector a clear outward via before the battery bus."""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,setplace,F,B
from geometry_guard_P3R1 import Guard
from body_keepouts_P3R1 import create
name,d,p,r=paths('power');b=k.LoadBoard(str(p));f=next(f for f in b.GetFootprints() if f.GetReference()=='J17');old=xy(f.GetPosition())
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA):continue
 if any(t.GetNetCode()==pad.GetNetCode() and t.IsOnLayer(F) and t.GetEffectiveShape(F).Collide(pad.GetEffectiveShape(F),mm(.001)) for pad in f.Pads()):b.Delete(t)
setplace(f,4.5,20,90,'F');create(b)
for uid in ['dcb7e942-65da-471b-b359-22d30078b4f6','04e0b57d-d6ba-4eb0-91a0-475e30c7ed77']:
 t=next((t for t in b.GetTracks() if t.m_Uuid.AsString()==uid),None)
 if t:b.Delete(t)
for net,points,w,l in [('/+5V_MOTION',[(6.45,20.625),(8.1,20.625)],.35,F),('/H_DUMP_D',[(74.9375,45),(76,45)],.6,B)]:
 assert Guard(b,net).line_clear(points[0],points[1],l,w),(net,points)
 track(b,net,points,w,l)
assert Guard(b,'/+5V_MOTION').via_clear((8.1,20.625),1)
via(b,'/+5V_MOTION',8.1,20.625,vd=1,dr=.45,grid=False)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'power_output_port.json').write_text(json.dumps(dict(J17_before_mm=old,J17_after_mm=[4.5,20],J17_outward_via_mm=[8.1,20.625],pad_neck_width_mm=.35,pad_neck_length_mm=1.65,pad_neck_status='DESIGN_GENERATED; thermal/current validation NOT_TESTED'),ensure_ascii=False,indent=2)+'\n')
print('Power output ports reserved',flush=True)
