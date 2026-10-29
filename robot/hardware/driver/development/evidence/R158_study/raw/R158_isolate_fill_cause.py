"""Native-refill counterfactuals to isolate power-plane splits; never layout candidates."""
import json,sys,shutil,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R158-fill-cause';out.mkdir(exist_ok=False);source=b/'R158C';py=str(Path(sys.executable).absolute());cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';records=[]
mutation='''import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
folder=Path(sys.argv[1]);case=sys.argv[2];path=folder/'MORI_Interface_C3.kicad_pcb';c=Copper(path);before=c.sha
if case=='remove_new_sampling_via':
 items=[v for v in c.vias if v.GetNetname()=='/UPS_BAT' and xy(v.GetPosition())==(45.3,8.6)];assert len(items)==1;v=items[0];change={'operation':'remove','uuid':uid(v),'snapshot':via_snapshot(c.board,v)};c.board.Remove(v)
else:
 id_='9fc6be27-25b2-4bce-8f44-98f39ccd1aa1' if case=='restore_3V3_via' else '4150016a-d870-4d6e-beae-177f9b3cdd3a';v=c.by_id[id_];pos=[46.6,10.35] if case=='restore_3V3_via' else [45.35,10.5];change={'operation':'restore_position','uuid':id_,'from':list(xy(v.GetPosition())),'to':pos};v.SetPosition(pcb.VECTOR2I(round(pos[0]*1e6),round(pos[1]*1e6)))
pcb.SaveBoard(str(path),c.board);(folder/'counterfactual.json').write_text(json.dumps({'source_sha256':before,'change':change,'not_a_design_candidate':True},indent=2)+'\\n')
'''
(out/'mutation.py').write_text(mutation)
for case in ['remove_new_sampling_via','restore_3V3_via','restore_UPS_via']:
 dest=out/case;shutil.copytree(source,dest);commands=[[py,str(out/'mutation.py'),str(dest),case],[cli,'pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(out/(case+'-drc.json')),str(dest/'MORI_Interface_C3.kicad_pcb')],[py,'robot/hardware/driver/development/scripts/audit_candidate.py','robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',str(dest/'MORI_Interface_C3.kicad_pcb'),str(out/(case+'-audit.json'))]]
 for i,argv in enumerate(commands):
  r=subprocess.run(argv,text=True,capture_output=True);records.append({'case':case,'step':i,'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode in ((0,5) if i==1 else (0,)),(case,i,r.stderr)
 a=json.loads((out/(case+'-audit.json')).read_text());d=json.loads((out/(case+'-drc.json')).read_text());print(json.dumps({'case':case,'opens':len(d['unconnected_items']),'other':len(d['violations']),'power_fails':[(x['net'],x['width_mm'],len(x['lost_pairs'])) for x in a['power_width'] if x['status']!='PASS'],'lost_nets':[(x['net'],len(x['lost_pad_pairs'])) for x in a['lost_pad_connections']]}),flush=True)
