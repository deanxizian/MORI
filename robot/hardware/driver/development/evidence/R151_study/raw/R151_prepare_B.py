"""Joint D301/ARMED placement preserving the HEAD_VM neck identified in native plots."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R151B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R151A-plan.json').read_text());p.update(revision='R151B',scope=__doc__)
p['translations'].append(dict(reference='D301',from_mm=[33.075,14.9],delta_mm=[0,.15]))
p['routes'][3]['points_mm']=[[32.1,13.15],[32.1,14.975],[32.025,15.05]]
u='b049d7c8-9984-50be-a63c-ab8f19b37c43';net=c.by_id[u].GetNetname()
p['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),position_mm=[32.6,16.0],reason='Clear translated D301 while widening separation from the GND anti-pad that bounds the HEAD_VM supply neck.'))
for u in ['01c0c62f-2e70-5cdb-b96b-7826f4ff753a','e0b746d4-193b-52fd-b359-e8159756c433','f4579267-fe8b-5c65-8e4e-a362a41e0428']:
    t=c.by_id[u];assert u not in p['delete_copper'];p['delete_copper'].append(u)
    p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'].extend([
 dict(net=net,layer='F.Cu',width_mm=.2,points_mm=[[32.86,14.69],[32.86,15.74],[32.6,16.0]]),
 dict(net=net,layer='B.Cu',width_mm=.2,points_mm=[[32.6,16.0],[31.75,16.0],[31.75,18.2]])])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
