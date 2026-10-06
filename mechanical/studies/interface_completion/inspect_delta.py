import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from interface_completion import change_regions
load_collections();assembled();bpy.context.view_layer.update()
b=json.loads((HERE/'baseline_geometry.json').read_text())
for n in ['Dock_Pad_0','Parking_Cradle']:
 print(n,'OLD',b['parts'][n],'NEW',geometry_record(bpy.data.objects[PREFIX+n]))
r=b['Head_Front'];old=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)));new=Solid(bpy.data.objects[PREFIX+'Head_Front']).m;zone=change_regions()['Head_Front']
for label,m in [('added',(new-old)-zone),('removed',(old-new)-zone)]:
 print(label,m.volume(),len(m.decompose()))
 for part in sorted(m.decompose(),key=lambda m:-m.volume())[:15]:print(part.volume(),part.bounding_box())
