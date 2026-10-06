"""Read-only geometric audit; writes only this study directory."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
names=['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Body_Upper']
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in names}
out={'source':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'derived':D,'parts':{}}
for n,s in ss.items():
 out['parts'][n]={'bounds_mm':list(zip(s.lo.tolist(),s.hi.tolist())),'slice_xz':s.m.rotate((90,0,0)).slice(0).to_polygons()}
 out['parts'][n]['slice_xz']=[p.tolist() for p in out['parts'][n]['slice_xz']]
 out['parts'][n]['horizontal_sections']={str(z):[p.tolist() for p in s.m.slice(z).to_polygons()] for z in [150,152,153.5,157,160.5,161,161.3,163.7,164.1,167.1,170,175,178]}
print('CURRENT_GAP_YOKE_BEARING',ss['Pitch_Yoke'].m.min_gap(ss['Yaw_Bearing'].m,20),flush=True)
print('CURRENT_GAP_BASE_BEARING',ss['Yaw_Base'].m.min_gap(ss['Yaw_Bearing'].m,20),flush=True)
for n,s in ss.items():print(n,s.lo,s.hi,flush=True)
(HERE/'inspection.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
