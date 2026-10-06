import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from speaker_geometry import speaker_transform
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
o=bpy.data.objects[PREFIX+'Body_Upper'];bm=bmesh.new();bm.from_mesh(o.data)
inv=speaker_transform().inverted()
rows=[]
for e in bm.edges:
 if not e.is_manifold:
  rows.append({'vertices':[(inv@o.matrix_world@v.co)[:] for v in e.verts],'faces':len(e.link_faces),'face_points':[[(inv@o.matrix_world@v.co)[:] for v in f.verts] for f in e.link_faces]})
save_json(Path(__file__).parent/'topology_diagnostic.json',rows)
print(json.dumps(rows))
