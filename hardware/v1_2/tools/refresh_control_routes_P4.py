"""Re-route three disturbed motion control nets with a reserved plane corridor."""
import pcbnew as k,sys
from helpers_P4 import paths
from layout_P3R1 import pt,F,B
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));action=sys.argv[1]
if action=='rip':
 k.SaveBoard(str(r/'before_control_refresh.kicad_pcb'),b)
 for t in list(b.GetTracks()):
  if t.GetNetname() in ['/CLR_N','/CHG_N','/USER_KEY_N']:b.Delete(t)
elif action=='reserve':
 for l in [F,B]:
  z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(l);z.SetZoneName('TEMP_THERMAL_CORRIDOR_P4');z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
  o=z.Outline();o.NewOutline()
  for x,y in [(34.5,28.3),(44.6,28.3),(44.6,34.5),(34.5,34.5)]:o.Append(k.FromMM(x),k.FromMM(y))
  b.Add(z)
elif action=='unreserve':
 for z in list(b.Zones()):
  if z.GetZoneName()=='TEMP_THERMAL_CORRIDOR_P4':b.Delete(z)
else:raise ValueError(action)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
