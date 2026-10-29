"""Retire obsolete local leads and join the actual existing GND endpoint."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R176B-plan.json').read_text())
p['revision']='R176C';p['scope']=__doc__+' Independent preparation; all LIMIT and power connections must be restored.'
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
ids=[uid(t) for t in c.segments if t.GetNetname() in ('Net-(U1701-LIMIT)','Net-(U1701-IN+)')]
ids+=['94097be9-7a4a-5f2f-a1eb-c11cabb5d174','c6f3715f-cbda-49d5-b266-4516a635d295']
for u in ids:
 if u in p['delete_copper']:continue
 t=c.by_id[u];p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes']=[r for r in p['routes'] if r['net']!='GND']
p['routes'].append(dict(net='GND',layer='B.Cu',width_mm=.2,points_mm=[[49.45,12.5],[50.35,12.5],[50.5,12.35]]))
out=b/'R176C-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(dict(revision=p['revision'],routes=len(p['routes']),deleted_tracks=len(p['delete_copper'])))
