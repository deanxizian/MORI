"""Native comparison of left-side RLIMIT placement; no adoption before restoration."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170C-plan.json';assert not out.exists()
p=json.loads((b/'R170B-plan.json').read_text());c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
p['revision']='R170C';p['scope']=__doc__
p['translations']=[dict(reference='R1701',from_mm=[47.275,9.7],delta_mm=[-4.525,.175],rotation_deg=270)]
for i in ['4da58487-f076-5185-8828-943f5727193f','fa9d0cc6-e3a3-5fe4-953f-d311beca4b4a','5be216ee-2f22-542d-b56c-b0fba2ef0a7b','ad8bf9ab-c57f-55b6-993f-db8012d24229']:
 t=c.by_id[i];p['delete_copper'].append(i);p['deleted_copper_expected'][i]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes']=[
 dict(net='/FAULT_N',layer='B.Cu',width_mm=.2,points_mm=[[45.05,11.35],[44.65,11.35],[43.6,10.3],[43.6,7.55]]),
 dict(net='Net-(U1701-LIMIT)',layer='B.Cu',width_mm=.2,points_mm=[[42.75,10.7],[43.425,11.375],[44.025,11.375],[44.025,12.35],[45.05,12.35]]),
 dict(net='/WHEEL_VM',layer='B.Cu',width_mm=.2,points_mm=[[42.2,7.825],[41.6,8.425],[41.6,11.4],[41.675,11.475],[41.675,12.15]])]
# Get the exact native WHEEL_VM spelling rather than infer its hierarchy.
p['routes'][2]['net']=c.by_id['fa9d0cc6-e3a3-5fe4-953f-d311beca4b4a'].GetNetname()
p.pop('endpoint_correction',None)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
