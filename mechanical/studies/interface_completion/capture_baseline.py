import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
load_collections();
for c in bpy.data.collections:
 if c.get('mori_owner')==OWNER:c.hide_viewport=False
assembled();bpy.context.view_layer.update()
names={r['host'] for r in P['interface_completion']['inserts']}|{'Head_Rear'}
r={'revision':'V1.2-M1.41','parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
for o in parts():
 n=o.name.removeprefix(PREFIX)
 if n in names:
  a=Solid(o);r[n]={'vertices_mm':a.v.tolist(),'triangles':a.f.tolist()}
(HERE/'baseline_geometry.json').write_text(json.dumps(r,ensure_ascii=False))
print('INTERFACE_BASELINE',len(r['parts']),names)
