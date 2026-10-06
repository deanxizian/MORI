"""Local diagnostic for a generated mesh; read-only, not qualification evidence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from export import topology
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
o=bpy.data.objects[PREFIX+'Speaker_Mount'];bm=bmesh.new();bm.from_mesh(o.data)
tr=Matrix(json.loads((ROOT/'reports/speaker_mount.json').read_text())['world_transform']).inverted()
edges=[e for e in bm.edges if not e.is_manifold]
print('BAD_EDGES',len(edges))
for e in edges[:30]:print('EDGE',len(e.link_faces),[list(tr@o.matrix_world@v.co) for v in e.verts])
o.data.calc_loop_triangles();v=np.array([tuple(o.matrix_world@p.co) for p in o.data.vertices]);f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64)
print('MANIFOLD_STATUS',manifold.Manifold(manifold.Mesh64(v,f)).status());bm.free()
