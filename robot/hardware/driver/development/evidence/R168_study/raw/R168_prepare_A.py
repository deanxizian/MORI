"""Prepare a jointly shifted Q/U/C group and explicitly relocate the ACT via.

Q1701 B (57.125,14)/270, U1702 F (58,15.25)/90 and C1702 B
(59.625,13.075)/90. The old ACT output transfer moves from (58.1,17.7)
to (55.825,15.4), freeing the bottom F ground return. The nine Q/U leads and
one C1702 power lead are replaced explicitly later. No source GND via moves.
This incomplete trial is not an accepted layout or a completed FAULT route.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R167B-plan.json').read_text());assert p['board_sha256']==c.sha
p.update(revision='R168A',scope=__doc__,placement_comparison='R168-pose-compare.json')
next(t for t in p['translations'] if t['reference']=='Q1701')['delta_mm']=[.375,-.25]
next(t for t in p['translations'] if t['reference']=='U1702')['delta_mm']=[.5,-.5]
p['translations'].append(dict(reference='C1702',from_mm=[59.5,13.2],delta_mm=[.125,-.125],rotation_deg=90))
u='1e9e8c5c-c13d-4f2a-a93b-75741c132e6b';t=c.by_id[u];assert t.GetNetname()=='MOTION_3V3'
p['delete_copper'].append(u);p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
u='74c0d925-81e9-4f8b-8224-202391f21e26';v=c.by_id[u];assert v.GetNetname()=='/17 {slash} Actuator_Overcurrent/ACT_UV_N'
p['move_vias']=[dict(uuid=u,source_expected=via_snapshot(c.board,v),position_mm=[55.825,15.4],reason='Move the original ACT_UV_N output transfer to the left of U1702, leaving the bottom ground return available. Both original F/B leads are explicitly replaced; all source GND vias stay fixed.')]
assert not p['routes'] and not p['vias']
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
