"""Trial Q1701 rotated 270 degrees with a 0.25 mm rightward translation.

Keep C1702 in its existing position and orientation. Reconstruct the two old
input leads explicitly in later steps; add only a prospective drain escape.
Q1701.2 is ACT_UV_N, not GND. This incomplete candidate is not adoptable.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R166C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
screen=json.loads((b/'R166-placement-screen.json').read_text());assert screen['source_sha256']==c.sha
pose=next(r for r in screen['combined_poses'] if r['Q1701']['position_mm']==[57.0,14.25] and r['Q1701']['rotation_deg']==270 and r['C1702']['position_mm']==[59.5,13.2] and r['C1702']['rotation_deg']==90)
deleted=['382cae9f-589a-4ec9-a79a-d9e4e5ee5d78','684e4239-41dc-4b65-8dea-69f18c4ad500','4fb23788-066b-4145-9618-25cf917ee7a9','540efe1c-baf2-481b-a656-71b6ae6b78f4','de64c402-7fb4-4a64-83cd-e23b14e8992d','e344ee9f-f225-4d49-962f-185077fc06b6']
expected={}
for u in deleted:
 t=c.by_id[u];assert isinstance(t,pcb.PCB_TRACK) and not isinstance(t,pcb.PCB_VIA)
 expected[u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
net='/FAULT_N'
plan=dict(revision='R166C',scope=__doc__,board_sha256=c.sha,translations=[dict(reference='Q1701',from_mm=[56.75,14.25],delta_mm=[.25,0],rotation_deg=270)],delete_copper=deleted,deleted_copper_expected=expected,routes=[dict(net=net,layer='B.Cu',width_mm=.2,points_mm=[[57,15.1875],[57.6,15.1875],[58.1,14.6875],[58.1,14.55]])],vias=[dict(net=net,position_mm=[58.1,14.55],diameter_mm=.5,drill_mm=.3)],placement_comparison='R166-placement-screen.json',adoption_prohibited=True)
out.write_text(json.dumps(plan,indent=2)+'\n');print(out)
