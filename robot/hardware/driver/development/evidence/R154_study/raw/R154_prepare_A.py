"""Independent local power-feed proposal, preserving the real narrow U1201 input land."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
drop=['b937e90f-41ec-4bc9-bc39-aad58b3709e5','8722d3b6-7a19-4458-ac60-865b470b4f8a','b5fbb078-87d1-432a-bec1-d734b6208dbd','37de691e-845b-4753-92e4-6d35e88f4106','1a512477-0860-46ba-8a5d-e236670b2551']
expected={u:{'net':c.by_id[u].GetNetname(),'layer':c.board.GetLayerName(c.by_id[u].GetLayer()),'width_mm':c.by_id[u].GetWidth()/1e6,'start_mm':xy(c.by_id[u].GetStart()),'end_mm':xy(c.by_id[u].GetEnd())} for u in drop}
u='1b3035a7-c9ba-44db-9674-ec974420a31b'
p={'revision':'R154A','scope':__doc__,'board_sha256':c.sha,'translations':[{'reference':'C1201','from_mm':[7.95,23.75],'delta_mm':[-.2,0]}],'move_vias':[{'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'position_mm':[8.75,23.05],'reason':'Move the original raw-input transfer within its existing allocation to allow a straight 0.50 mm trunk clear of the actual neighbouring U1201 pads; preserve via size and all native rules.'}],'delete_copper':drop,'deleted_copper_expected':expected,'routes':[{'net':'/HEAD_6V_RAW','layer':'F.Cu','width_mm':.5,'points_mm':[[8.75,23.05],[8.75,26.225],[8.0,26.225]]},{'net':'/HEAD_6V_RAW','layer':'F.Cu','width_mm':.5,'points_mm':[[7.75,24.75],[8.95,24.75]]},{'net':'/HEAD_6V_RAW','layer':'F.Cu','width_mm':.3,'points_mm':[[8.95,24.75],[9.35,24.75]]}], 'design_notes':['The unchanged input pin is only 0.30 mm high; the local 0.30 mm escape is intentional and must not be replaced by a false 0.48 mm full-terminal claim.','The aim is a wider trunk to both local input capacitors and a short real-pad escape, not current or physical qualification.']}
out=b/'R154A-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n');print(str(out))
