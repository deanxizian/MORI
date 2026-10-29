"""Remove the obsolete single-layer D2 transfer from the independent G trial.
No source/frozen evidence is overwritten; native refill and all regressions follow.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143J-plan.json';assert not out.exists()
c=Copper(str(b/'R143G/MORI_Interface_C3.kicad_pcb'));v=c.by_id['819eb181-4e28-4093-bf9b-3792433636d0']
contacts=via_contact_layers(c.board,v);assert contacts==['B.Cu']
p={'revision':'R143J','board_sha256':c.sha,'purpose':__doc__,'remove_obsolete_vias':[{'uuid':uid(v),'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':contacts,'reason':'The completed D2 route is entirely on B.Cu. Native G DRC reports this exact via as dangling; both B tracks meet at its exact centre, so no layer transfer remains.'}]}
out.write_text(json.dumps(p,indent=2)+'\n')
