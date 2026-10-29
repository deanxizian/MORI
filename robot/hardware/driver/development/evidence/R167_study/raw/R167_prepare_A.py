"""Prepare the least-movement screened U1702/Q1701 group from canonical R165M.

Q1701 moves to B (57,14), 270 degrees. U1702 moves to F (58.25,15.25),
retaining 180 degrees. C1702 and every via stay fixed. Three U1702 F leads
and six original Q input leads are removed explicitly for joint reconstruction.
This is an incomplete preparation, not an adoptable circuit.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R167A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R166E-plan.json').read_text());assert c.sha==p['board_sha256']
screen=json.loads((b/'R167-joint-pose-screen.json').read_text());assert screen['canonical_source_sha256']==c.sha
pose=next(r for r in screen['poses'] if r['position_mm']==[58.25,15.25] and r['rotation_deg']==180);assert pose['legal_port_grid_points']==16 and not pose['requires_old_ACT_via_relocation']
p.update(revision='R167A',scope=__doc__,placement_comparison='R167-joint-pose-screen.json')
p['translations'].append(dict(reference='U1702',from_mm=[57.5,15.75],delta_mm=[.75,-.5],rotation_deg=180))
for id_ in screen['prospectively_replaced_U1702_F_tracks']:
 assert id_ not in p['delete_copper'];t=c.by_id[id_]
 p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
assert not p['routes'] and not p['vias']
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
