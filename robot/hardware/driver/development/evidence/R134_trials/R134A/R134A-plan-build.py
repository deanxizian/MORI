from pathlib import Path
import sys,json
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
remove=['a577a476-5966-4c4b-942c-5de414ca3445','ff85e629-76e5-48f7-8a6f-4c593c58e84d','4c96b857-f333-414f-a5e7-93f059f566d9','dff1636d-ddeb-46e3-a401-1e505f5c268f','9ea26d74-6a52-4cf5-8732-b87340b06df4']
old={i:{'net':c.by_id[i].GetNetname(),'layer':c.board.GetLayerName(c.by_id[i].GetLayer()),'width_mm':c.by_id[i].GetWidth()/1e6,'start_mm':list(xy(c.by_id[i].GetStart())),'end_mm':list(xy(c.by_id[i].GetEnd()))} for i in remove}
v='0c2b6dad-30ad-4479-bfea-d57088d24c72'
p={'revision':'R134A','board_sha256':c.sha,'scope':'Independent U402 fanout group revision: move R407, reuse old HEAD_TX hole for 2Y, retain old HEAD_TX connection on a new adjacent hole. Not an adopted layout.','translations':[{'reference':'R407','from_mm':[56.5,25.5],'delta_mm':[-.25,.6]}],'delete_copper':remove,'deleted_copper_expected':old,'reassign_vias':[{'uuid':v,'source_expected':via_snapshot(c.board,c.by_id[v]),'net':'Net-(U401-2Y)'}],'routes':[{'net':'GND','layer':'B.Cu','width_mm':.2,'points_mm':[[55.75,25],[56.025,25.275],[56.25,25.275]]},{'net':'/03 {slash} Motor_Buses/HEAD_BUS','layer':'B.Cu','width_mm':.2,'points_mm':[[56.9,26.125],[56.9,26.6],[56.575,26.925],[56.25,26.925]]},{'net':'/01 {slash} Core/HEAD_TX','layer':'B.Cu','width_mm':.2,'points_mm':[[55.8,23.35],[55.8,23.7],[56.15,24.05]]},{'net':'/01 {slash} Core/HEAD_TX','layer':'In3.Cu','width_mm':.2,'points_mm':[[56.15,24.05],[56.15,25.2],[55.4,25.95]]},{'net':'Net-(U401-2Y)','layer':'B.Cu','width_mm':.2,'points_mm':[[55.15,23.35],[55.15,23.8],[55.4,24.05]]}],'vias':[{'net':'/01 {slash} Core/HEAD_TX','position_mm':[56.15,24.05],'diameter_mm':.5,'drill_mm':.3}]}
Path('robot/.state/c3-completion/trials/R134A-plan.json').write_text(json.dumps(p,indent=2)+'\n')
