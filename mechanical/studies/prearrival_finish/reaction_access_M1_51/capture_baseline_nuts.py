"""Read raw vertex/triangle order from the immutable M1.51 snapshot."""
from pathlib import Path
import sys,json,hashlib
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from validate import Solid
source=PROJECT/'mechanical/revisions/V1.2-M1.51_before_nut_alignment/mechanical/mori_v1_2.blend'
assert Path(bpy.data.filepath).resolve()==source
before=json.loads((OUT/'inspection.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==before['sources']['mechanical/mori_v1_2.blend']
load_collections();assembled();bpy.context.view_layer.update()
for name in ['Yaw_Reaction_Clamp_Nut','Yaw_Reaction_Retainer_Nut']:
    s=Solid(bpy.data.objects[PREFIX+name])
    assert hashlib.sha256(s.v.tobytes()+s.f.tobytes()).hexdigest()==before['native_fingerprints'][name]
    np.savez_compressed(OUT/(name+'_native_baseline.npz'),vertices_mm=s.v,triangles=s.f)
print('RAW_BASELINE_NUTS_CAPTURED',flush=True)
