import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
folder=Path(sys.argv[1]);case=sys.argv[2];path=folder/'MORI_Interface_C3.kicad_pcb';c=Copper(path);before=c.sha
if case=='remove_new_sampling_via':
 items=[v for v in c.vias if v.GetNetname()=='/UPS_BAT' and xy(v.GetPosition())==(45.3,8.6)];assert len(items)==1;v=items[0];change={'operation':'remove','uuid':uid(v),'snapshot':via_snapshot(c.board,v)};c.board.Remove(v)
else:
 id_='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1' if case=='restore_3V3_via' else '4150016a-d870-4d6e-beae-177f9b3cdd3a';v=c.by_id[id_];pos=[46.6,10.35] if case=='restore_3V3_via' else [45.35,10.5];change={'operation':'restore_position','uuid':id_,'from':list(xy(v.GetPosition())),'to':pos};v.SetPosition(pcb.VECTOR2I(round(pos[0]*1e6),round(pos[1]*1e6)))
pcb.SaveBoard(str(path),c.board);(folder/'counterfactual.json').write_text(json.dumps({'source_sha256':before,'change':change,'not_a_design_candidate':True},indent=2)+'\n')
