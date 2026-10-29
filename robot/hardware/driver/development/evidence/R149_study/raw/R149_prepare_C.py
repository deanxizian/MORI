"""Correct B using actual D301 body/pad geometry and retain the front CLR corridor above ARMED."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R149C-plan.json';assert not out.exists();c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R149B-plan.json').read_text());p.update(revision='R149C',scope=__doc__)
p['translations'].append(dict(reference='D301',from_mm=[33.075,14.9],delta_mm=[0,.15]))
p['move_vias'][0]['position_mm']=[31.86,5.75]
p['move_vias'][1]['position_mm']=[32.45,14.0]
u='a64ead90-f8fb-47e5-9d8d-700e6f43096f';t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'][1]['points_mm']=[[31.45,7.0375],[31.45,6.375],[31.86,5.965],[31.86,5.75]]
p['routes'][2]['points_mm']=[[31.86,5.75],[31.86,6.4],[31.5,6.76],[30.95,6.76],[30.44,6.25],[26.6,6.25]]
p['routes'][3]['points_mm']=[[32.1,13.15],[32.1,13.65],[32.45,14.0],[32.025,14.425],[32.025,15.05]]
p['routes'][4]['points_mm']=[[32.45,14.0],[32.6,13.85],[35.2,13.85]]
p['routes'][5]['points_mm']=[[32.3,13.0],[32.45,13.15],[32.45,14.0]]
p['routes'][6]['points_mm']=[[33.5,13.3625],[33.5,13.525],[34.875,14.9],[35.75,14.75]]
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
