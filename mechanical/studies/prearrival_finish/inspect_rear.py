"""Locate coincident export edges in the current rear shell; read-only."""
import sys, json, collections, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'mechanical/scripts'))
from common import *
from validate import Solid
from export import topology

load_collections()
assembled()
bpy.context.view_layer.update()
o = bpy.data.objects[PREFIX + 'Head_Rear']
o.data.calc_loop_triangles()
vs = np.array([list(v) for v in vertices_world(o)])
fs = np.array([tuple(t.vertices) for t in o.data.loop_triangles])
unique, inv = np.unique(vs.astype(np.float32), axis=0, return_inverse=True)
wf = inv[fs]
edges = collections.defaultdict(list)
for i, f in enumerate(wf):
    for a, b in zip(f, np.roll(f, -1)):
        edges[tuple(sorted((a, b)))].append(i)
bad = []
for (a, b), faces in edges.items():
    if len(faces) != 2:
        bad.append(dict(edge_mm=unique[[a,b]].tolist(), faces=faces,
                        triangles_mm=unique[wf[faces]].tolist(),
                        old_indices=fs[faces].tolist()))
m = Solid(o).m
report = dict(source_sha256=hashlib.sha256((PROJECT_ROOT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),
              indexed_topology=topology(vs, fs), welded_topology=topology(unique,wf),
              kernel_status=str(m.status()), volume_mm3=m.volume(), bad_edges=bad)
(HERE/'rear_inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2), flush=True)
np.savez_compressed(HERE/'rear_mesh.npz', vertices=vs, faces=fs)
