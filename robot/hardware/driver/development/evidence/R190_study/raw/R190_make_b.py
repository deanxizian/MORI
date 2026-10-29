"""Close the five-part placement trial without retaining either single-layer hole.

RAW is still unconnected; the old wheel hole site is released for future routing.
No connection or engineering-completion claim follows from this cleanup.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R190B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R190A-plan.json').read_text());assert p['board_sha256']==c.sha
p.update(revision='R190B',scope=__doc__)
p['routes']=[r for r in p['routes'] if r['net']!='/HEAD_6V_RAW']
p['reassign_vias']=[r for r in p['reassign_vias'] if r['net']!='/HEAD_6V_RAW']
p['remove_obsolete_vias']=[dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),remaining_contact_layers=layers,reason=reason) for u,layers,reason in [
 ('5cc2b6b0-e919-4910-b0af-8902a95393d9',[],'Both old wheel tails are explicitly retired and the complete wheel net restored through the former OV hole; no remaining transfer.'),
 ('0637843e-2a2e-4b72-9de7-92b1c08ca96b',['F.Cu'],'The retired OV In2 path is replaced by the explicit F.Cu junction. Only the same-face F.Cu path remains; removing this hole preserves that junction.')]]
with out.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
