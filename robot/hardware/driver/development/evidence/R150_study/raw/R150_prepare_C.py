"""Joint OV reroute and local reference repair, rebuilt from accepted R148E.

The complete old OV branch is restored on its existing R13-permitted In2 layer
without new vias. Exact terminal reconstruction was screened against the actual
R150B copper and reference geometry. This remains an independent candidate.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R150C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R150B-plan.json').read_text());p.update(revision='R150C',scope=__doc__)
p['move_vias'][0]['position_mm']=[31.91,5.85]
p['move_vias'][1]['position_mm']=[32.45,13.95]
p['routes'][1]['points_mm']=[[31.45,7.0375],[31.45,6.31],[31.91,5.85]]
p['routes'][2]['points_mm']=[[31.91,5.85],[31.91,6.4],[31.55,6.76],[30.81,6.76],[30.3,6.25],[26.6,6.25]]
p['routes'][4]['points_mm']=[[32.45,13.95],[32.55,13.85],[35.2,13.85]]
p['routes'][5]['points_mm']=[[32.3,13.0],[32.45,13.15],[32.45,13.95]]
p['routes'][7]['points_mm']=[[32.1,13.95],[32.45,13.95]]
p['routes'][-1]['points_mm']=[[32.86,16.0],[31.75,16.0],[31.75,18.2]]
for u in ['f4579267-fe8b-5c65-8e4e-a362a41e0428','2a81b3ba-e1f5-4e6b-8a67-d70f9cffe636']:
    t=c.by_id[u]; assert u not in p['delete_copper']
    p['delete_copper'].append(u)
    p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
u='888a9e42-c789-49e6-8028-2f14677c4710'
p['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),position_mm=[34.85,13.0],reason='Separate the ACT_BAT_SWITCHED reference void from the front CLR corridor; preserve original 0.60/0.30 mm via and 0.60 mm feed.'))
p['routes'].append(dict(net=c.by_id[u].GetNetname(),layer='F.Cu',width_mm=.6,points_mm=[[34.85,12.5],[34.85,13.0]]))
p['routes'].append(dict(net='Net-(U1301-INB-_{slash}_OV)',layer='In2.Cu',width_mm=.2,points_mm=[[60.9,19.35],[60.9,23.1],[61.95,24.15],[61.95,25.6],[64.275,27.925],[64.275,28.8]]))
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
