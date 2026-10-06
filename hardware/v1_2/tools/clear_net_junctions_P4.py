"""Replace two 45-degree CLR_N crossings with orthogonal T junctions."""
import pcbnew as k,json
from helpers_P4 import paths
from geometry_guard_P3R1 import Guard
from layout_P3R1 import track,F,B
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_CLR_junctions.kicad_pcb'),b);log=[]
for uid,paths_mm in [('647049af-1e87-44b1-99f5-7ebd45085bea',[[(27.75,15.75),(27.75,15.2)],[(26.75,14.75),(26.75,15.2)]]),('85cb4b2a-b490-4814-bf1b-26cb55d33b0e',[[(9.9,18.65),(10.4,18.65)],[(11.95,16.6),(10.4,16.6)]])]:
 t=next(t for t in b.GetTracks() if t.m_Uuid.AsString()==uid);backup=t.Duplicate();b.Delete(t)
 g=Guard(b,'/CLR_N');ok=all(g.line_clear(a,z,B) for a,z in paths_mm)
 if ok:
  for ps in paths_mm:track(b,'/CLR_N',ps,.2,B)
  log.append(dict(replaced=uid,branches_mm=paths_mm))
 else:b.Add(backup);print('blocked',uid)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'CLR_junctions.json').write_text(json.dumps(log,indent=2)+'\n')
