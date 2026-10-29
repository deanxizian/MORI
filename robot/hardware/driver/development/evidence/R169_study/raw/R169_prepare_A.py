"""Independent U1701 half-turn comparison from canonical R168G.

Keep the physical package location and all source vias. Explicitly retire the
old IN+/IN-/LIMIT pin leads and two ground terminal segments that would touch
different pins after the half-turn. Fixed via windows in owned native guards
are reconstructed with the existing explicit supported operation. This is an
incomplete comparison; every original signal, power and RLIMIT return must be
restored before adoption. No physical or manufacturer qualification is implied.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R169A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
delete=[uid(t) for t in c.segments if t.GetNetname() in ['Net-(U1701-IN+)','Net-(U1701-IN-)','Net-(U1701-LIMIT)']]
delete+=['7f8155d8-ae9b-5681-abf0-b9bd90943193','4e3cff17-d7fe-4cb4-87f2-0dfef758262e']
expected={}
for u in delete:
 t=c.by_id[u];expected[u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p=dict(revision='R169A',scope=__doc__,board_sha256=c.sha,translations=[dict(reference='U1701',from_mm=[47.25,12.35],delta_mm=[0,0],rotation_deg=180,reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True)],delete_copper=delete,deleted_copper_expected=expected,routes=[],vias=[],adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out,'explicitly retired tracks',len(delete))
