"""Build the actual R176A same-face proposals, explicitly recentering a moved via lead."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
p=json.loads((b/'R176A-plan.json').read_text())
p['revision']='R176B'
p['scope']=__doc__+' All source acceptance rules and retained connections remain mandatory.'
r=json.loads((b/'R176A-R176-loops/searches.json').read_text())
assert r['source_sha256']==hashlib.sha256((b/'R176A/MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()
p['routes']=r['routes'];p['vias']=r['vias']
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
u='3c59ab5a-ed77-4497-bfe1-918eab519360';t=c.by_id[u]
assert u not in p['delete_copper']
p['delete_copper'].append(u)
p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'].append(dict(net='MOTION_3V3',layer='F.Cu',width_mm=.2,points_mm=[[48.325,14.1],[48.175,14.25],[47.775,14.25]]))
out=b/'R176B-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(dict(revision=p['revision'],routes=len(p['routes']),deleted_tracks=len(p['delete_copper'])))
