"""Native diagnostic of the complete RAW path found without extra supply reservations.

This is NOT a power-preservation waiver. Refill, all source connectivity/width,
reference and native requirements must pass before any acceptance decision.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R190C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R190A-plan.json').read_text());d=json.loads((b/'R190A-R190-unreserved-RAW/plan.json').read_text());assert p['board_sha256']==c.sha
assert d['board_sha256']==json.loads((b/'R190A-audit.json').read_text())['board_sha256']
p.update(revision='R190C',scope=__doc__)
p['routes']+=d['routes'];p['vias']=d['vias'];assert not d['activate_pth_layers']
u='0637843e-2a2e-4b72-9de7-92b1c08ca96b'
p['remove_obsolete_vias']=[dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),remaining_contact_layers=['F.Cu'],reason='Retire the former OV In2 transfer; the explicit F.Cu junction retains the complete OV net.')]
with out.open('x') as f:json.dump(p,f,indent=2);f.write('\n')
