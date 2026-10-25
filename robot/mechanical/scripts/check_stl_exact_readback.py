"""Diagnose vertex welding in the STL reader without changing source geometry."""
import sys,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from export import topology
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
manifest=json.loads((ROOT/'reports/export_manifest.json').read_text());rows=[]
for row in manifest['parts']:
    path=ROOT/row['file'];data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    vertices=[];faces=[];lookup={};normals=[]
    for k in range(n):
        record=struct.unpack_from('<12fH',data,84+k*50);ids=[];normals.append(record[:3])
        for j in range(3):
            xyz=tuple(record[3+j*3:6+j*3])
            if xyz not in lookup:lookup[xyz]=len(vertices);vertices.append(xyz)
            ids.append(lookup[xyz])
        faces.append(ids)
    t=topology(vertices,faces,normals)
    before=set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path),global_scale=1.0,use_scene_unit=False,forward_axis='Y',up_axis='Z')
    added=[o for o in bpy.data.objects if o not in before];o=added[0];o.data.calc_loop_triangles()
    imported=topology(vertices_world(o),[tuple(t.vertices) for t in o.data.loop_triangles])
    rows.append(dict(id=row['id'],rounded_reader=row['topology'],exact_reader=t,blender_import=imported))
    for ob in added:
        me=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
    print('STL_EXACT_READBACK',row['id'],t,imported,flush=True)
save_json(ROOT/'reports/stl_exact_readback_diagnostic.json',rows)
