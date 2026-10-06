"""Give the head-output ground terminal room for four thermal spokes."""
import pcbnew as k,json,math
from helpers_P4 import paths
from layout_P3R1 import setplace,pt,xy,F,B
from body_keepouts_P3R1 import create
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_J9_clearance_shift.kicad_pcb'),b)
old=k.LoadBoard(str(r/'before_last_ground_return.kicad_pcb'))
for t in list(b.GetTracks()):
 if t.GetNetname()=='/CHG_N':b.Delete(t)
for t in old.GetTracks():
 if t.GetNetname()=='/CHG_N':b.Add(t.Duplicate())
f=next(f for f in b.GetFootprints() if f.GetReference()=='J9');oldpads=[(q.GetNetname(),xy(q.GetPosition())) for q in f.Pads()]
# Move terminal-attached endpoints with the connector; keep widths intact.
for t in b.GetTracks():
 if t.Type()==k.PCB_VIA_T:continue
 for get,put in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
  x,y=xy(get())
  if any(t.GetNetname()==net and math.dist((x,y),pos)<.05 for net,pos in oldpads):put(pt(x+1,y))
setplace(f,52.5,49,0,'F');create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'head_output_connector_shift.json').write_text(json.dumps(dict(before_mm=[51.5,49],after_mm=[52.5,49],reason='Increase distance from CHG_N to the GND terminal thermal spokes without creating a signal-line jog',pin_assignment_unchanged=True),indent=2)+'\n')
