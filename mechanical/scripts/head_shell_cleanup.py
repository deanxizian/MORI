"""Remove only the four reviewed numerical remnants, not design features."""
from common import *
from mesh_components import components

def apply_head_shell_cleanup():
    if P['revision']!='V1.2-M1.52':return
    o=bpy.data.objects[PREFIX+'Head_Front'];bpy.context.view_layer.update()
    verts=[tuple(o.matrix_world@v.co) for v in o.data.vertices]
    faces=[tuple(p.vertices) for p in o.data.polygons]
    groups=components(verts,faces)
    if len(groups)==1:
        save_json(ROOT/'reports/head_shell_cleanup.json',{'status':'PASS','removed_components':0,'remaining_components':1});return
    fragments=groups[1:]
    if len(fragments)!=4:raise RuntimeError('Unexpected Head_Front islands; inspect before changing geometry')
    for g in fragments:
        x,y,z=g['bounds_xyz_mm']
        if not (g['volume_mm3_abs']<.001 and 44.8<min(abs(v) for v in x)<45.8 and max(abs(v) for v in x)<45.8 and .29<y[0]<=y[1]<2.35 and 255.27<z[0]<=z[1]<255.79):
            raise RuntimeError('Unreviewed Head_Front fragment; automatic removal refused')
    expected={tuple(verts[v] for v in faces[i]) for i in groups[0]['faces']}
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
    removed={v for g in fragments for v in g['vertices']}
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in removed],context='VERTS')
    bm.to_mesh(o.data);bm.free();o.data.update();SOLIDS.pop(o.name,None)
    after={tuple(tuple(o.matrix_world@o.data.vertices[v].co) for v in p.vertices) for p in o.data.polygons}
    # Polygon vertex order can rotate during a BMesh roundtrip; compare cycles.
    canonical=lambda fs:{min(f[i:]+f[:i] for i in range(len(f))) for f in fs}
    if canonical(expected)!=canonical(after):raise RuntimeError('Head_Front main component changed')
    save_json(ROOT/'reports/head_shell_cleanup.json',{'status':'PASS','removed_components':4,'remaining_components':1,'main_faces_preserved_exactly':True,'removed':[{'faces':len(g['faces']),'volume_mm3_abs':g['volume_mm3_abs'],'bounds_xyz_mm':g['bounds_xyz_mm']} for g in fragments],'scope':'Numerical detached remnants only; no dimensional or manufacturing qualification'})
