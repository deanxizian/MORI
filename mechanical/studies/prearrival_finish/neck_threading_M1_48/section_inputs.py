"""Export actual native sections for the provenance/local collision review."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path(bpy.data.filepath)
audit=json.loads((HERE/'source_audit.json').read_text())
assert sha(source)==audit['source_main_sha256']
load_collections();assembled();bpy.context.view_layer.update()
names=['Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Pitch_Yoke','Head_Lower_Guard','Body_Upper','Load_Frame','Yaw_Keeper']
solids={n:Solid(bpy.data.objects[PREFIX+n]).m for n in names if PREFIX+n in bpy.data.objects}
for n in ['Yaw_Base','Pitch_Yoke']:
    a=np.load(HERE.parent/'harness_A8/terminal_threading/cleaned'/f'{n}.npz')
    solids['candidate_'+n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
def polygons(s):return [p.tolist() for p in s.to_polygons()]
radial={str(angle):{n:polygons(m.rotate([0,0,-angle]).rotate([90,0,0]).slice(0)) for n,m in solids.items()} for angle in [0,45,90,135]}
horizontal={str(z):{n:polygons(m.slice(z)) for n,m in solids.items()} for z in [139,141.5,143,145.6,146,147,150,156,160,164,166,170,174,178,182,186]}
data=dict(source_main_sha256=sha(source),script_sha256=sha(__file__),radial=radial,horizontal=horizontal,
          bounds={n:list(m.bounding_box()) for n,m in solids.items()},units='mm',geometry_applied=False)
(HERE/'section_inputs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('NATIVE_SECTIONS',len(solids),flush=True)
