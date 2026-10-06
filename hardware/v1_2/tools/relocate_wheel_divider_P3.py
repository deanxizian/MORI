"""Move the voltage divider into the free output-side bay; preserve resistor values/nets."""
import pcbnew as k,json
from layout_P3 import paths,xy,pt,F,B,via,track,setplace
from geometry_guard_P3 import Guard,obstacles
from route_local_P3 import connect
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_divider_move.kicad_pcb'),b);fps={f.GetReference():f for f in b.GetFootprints()}
oldg=pt(36.325,24)
for t in list(b.GetTracks()):
 if t.GetNetname()=='/WHEEL_ADC' and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<40:b.Delete(t)
 elif t.GetNetname()=='/GND' and (t.GetStart()==oldg or t.GetEnd()==oldg):b.Delete(t)
# Compare a small group-placement grid; prefer the bay nearest both endpoints.
chosen=None
for yy in [26.5,27,25.5,28,29,25,30,24.5]:
 for xx in [46,47,48,45,44,49]:
  setplace(fps['R52'],xx,yy,0,'B');setplace(fps['R53'],xx+3,yy,0,'B')
  good=True
  for ref in ['R52','R53']:
   for q in fps[ref].Pads():
    if not Guard(b,str(q.GetNetname())).clear(xy(q.GetPosition()),B,.95):good=False;break
   if not good:break
  if not good:continue
  start=(xx+.825,yy);end=(xx+2.175,yy)
  if not Guard(b,'/WHEEL_ADC').line_clear(start,end,B):continue
  chosen=(xx,yy);break
 if chosen:break
assert chosen,'no legal divider group placement'
xx,yy=chosen;print('divider new centres',chosen,(xx+3,yy),flush=True)
track(b,'WHEEL_ADC',[(xx+.825,yy),(xx+2.175,yy)],.2,B)
k.SaveBoard(str(p),b);log=[]
for net,a,z,al,zl in [('/W_VM',(xx-.825,yy),(46.775,23.905),[B],[B]),('/WHEEL_ADC',(xx+1.5,yy),(46.875,33),[B],[F,B])]:
 try:log.append(connect(b,net,a,z,al,zl,(80,55),step=.05));k.SaveBoard(str(p),b)
 except RuntimeError as e:print(e,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'divider_move.json').write_text(json.dumps(log,indent=2)+'\n')
