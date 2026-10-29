"""Independent source-pinned F: deliberate feed route and corridor; no adopted geometry."""
import json,sys
from pathlib import Path
from shapely.geometry import Polygon
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
p=json.loads((b/'R153E-plan.json').read_text())
p['revision']='R153F'
p['scope']=__doc__
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert p['board_sha256']==c.sha
p['move_vias'][0]['position_mm']=[6.6,17.8]
p['move_vias'][0]['reason']='Compare a small upper-left relocation with unchanged 0.8/0.4 mm power via geometry to widen the new RAW corridor while retaining old HEAD_VM, OVLO reference and all native clearances.'
p['routes']=p['routes'][:1]
p['routes'] += [
 {'net':'/HEAD_VM','layer':'B.Cu','width_mm':.6,'points_mm':[[6.65,18.695],[6.65,17.85],[6.6,17.8]]},
 {'net':'/HEAD_6V_RAW','layer':'F.Cu','width_mm':.5,'points_mm':[[13.4,18.3],[13.4,21.3],[11.5,21.3],[11.5,22.8]]}
]
for u in ['3c5411b1-656e-4f4e-97bb-f311763817d5','739105c0-649c-444d-9fc3-943acff8a27f','121d1490-1d3a-4f98-852d-a5d848c7af41']:
 t=c.by_id[u];p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
spec=p['power_zone_expansions'][0]
spec['union_patch_mm']=[[3.6,16.3],[5,16.3],[5.8,17.1],[5.8,18.1],[6.1,18.4],[7.4,18.4],[7.4,21.6],[3.5,21.6],[3.5,17.2]]
z=next(z for z in c.zones if uid(z)==spec['uuid']);old=polyset(z.Outline())
spec['expected_added_area_mm2']=old.union(Polygon(spec['union_patch_mm'])).area-old.area
out=b/'R153F-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'plan':str(out),'source':c.sha,'area':spec['expected_added_area_mm2']}))
