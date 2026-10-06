"""Reuse checked geometry helpers on the isolated P4 projects only."""
import sys,runpy
import route_local_P4
sys.modules["route_local_P3R1"]=route_local_P4
from pathlib import Path
import layout_P3R1 as base
H=Path(__file__).resolve().parents[1]
def paths(kind):
 name='MORI_'+kind+'_P4';d=H/'kicad'/name;r=H/'layout_P4/reports'/name;r.mkdir(parents=True,exist_ok=True)
 return name,d,d/(name+'.kicad_pcb'),r
base.paths=paths
if __name__=='__main__':
 helper,kind=sys.argv[1:3];sys.argv=[helper,kind]+sys.argv[3:]
 source=(H/'tools'/helper).read_text()
 if helper=='close_networks_P3R1.py':
  # Do not use the historic unconditional merge/snap cleanup. Native checked
  # transactional cleanup is a separate action after all connections exist.
  source=source[:source.index('\nmerge_lines(b)')]+"\nk.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)\n"
 source=source.replace("H/'layout_P3R1'","H/'layout_P4'").replace("R/'layout_P3R1'","R/'layout_P4'")
 source=source.replace("vd=(.8 if kind=='motion' else .6)","vd=.8")
 source=source.replace("step=(.05 if \"--fine\" in sys.argv else .1),width=.2", "step=(.05 if \"--fine\" in sys.argv else .1),width=(.6 if kind=='rear' and net in ['/VBUS_RAW','/VBUS_FUSED'] else .2)")
 source=source.replace("'imu':(20,16)","'imu':(20,16),'rear':(24,25)")
 if helper=='polish_P3R1.py':
  source=source.replace("mapping={};changes={}","mapping={};changes={}; w,h=json.loads((d/'connectivity.json').read_text())['size']")
  source=source.replace("ok=not any(s.Collide(p,margin) for s in masks[g.GetLayer()])", "ok=(.51 < k.ToMM(p.x) < w-.51 and .51 < k.ToMM(p.y) < h-.51) and not any(s.Collide(p,margin) for s in masks[g.GetLayer()])")
 exec(compile(source,str(H/'tools'/helper),'exec'),{'__name__':'__main__','__file__':str(H/'tools'/helper)})
