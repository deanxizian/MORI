"""Reuse presentation bytes only after strict old/new/embedded-source equality."""
from pathlib import Path
import sys, json, hashlib, datetime
HERE=Path(__file__).resolve().parent;M=HERE.parents[2]
sys.path.insert(0,str(M/'scripts'))
from common import *
from assembly_animation import signature

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def simple(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    try:return list(v)
    except TypeError:return str(type(v))
def material_record(m):
    if not m:return None
    return dict(name=m.name,color=list(m.diffuse_color),
        nodes=[dict(name=n.name,type=n.bl_idname,inputs=[(s.name,simple(s.default_value)) for s in n.inputs if hasattr(s,'default_value')]) for n in m.node_tree.nodes] if m.use_nodes else [],
        links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.use_nodes else [])
def capture(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=scene;load_collections()
    for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
    assembled();bpy.context.view_layer.update()
    rows={};actors=[]
    for o in sorted(scene.objects,key=lambda x:x.name):
        if o.type!='MESH' or o.get('mori_owner')!=OWNER:continue
        if o.get('role') not in ['part','routing','display_content']:continue
        h=hashlib.sha256();o.data.calc_loop_triangles()
        for value in [np.asarray(o.matrix_world,dtype=np.float64),
                      np.asarray([v.co[:] for v in o.data.vertices],dtype=np.float32),
                      np.asarray([t.vertices[:] for t in o.data.loop_triangles],dtype=np.int32),
                      np.asarray([p.material_index for p in o.data.polygons],dtype=np.int32),
                      np.asarray([p.use_smooth for p in o.data.polygons],dtype=np.uint8),
                      np.asarray([e.use_edge_sharp for e in o.data.edges],dtype=np.uint8)]:h.update(value.tobytes())
        if o.data.has_custom_normals:
            h.update(np.asarray([n.vector[:] for n in o.data.corner_normals],dtype=np.float32).round(6).tobytes())
        h.update(json.dumps([material_record(s.material) for s in o.material_slots],sort_keys=True).encode())
        h.update(json.dumps({k:o.get(k) for k in ['category','group','role','data_status']},sort_keys=True).encode())
        rows[o.name]=h.hexdigest()
        if o.get('group') not in ['dock','coupon']:actors.append(o)
    return rows,signature(actors),len(actors)

old=HERE/'before/mori_v1_2.blend';new=M/'mori_v1_2.blend';animation=M/'mori_assembly_animation.blend'
old_hash=digest(old);new_hash=digest(new)
manifest_path=M/'animation/manifest.json';manifest=json.loads(manifest_path.read_text())
assert manifest['source_blend_sha256']==old_hash
before,bs,bc=capture(old);after,asig,ac=capture(new);embedded,es,ec=capture(animation)
changed=[n for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)]
embedded_bad=[n for n in before if before[n]!=embedded.get(n)]
assert not changed,changed
assert not embedded_bad,embedded_bad
assert bs==asig==es==manifest['source_geometry_signature']
assert bc==ac==ec==manifest['actor_count']
assert digest(M/'animation/MORI_assembly.mp4')==manifest['video']['sha256']
assert digest(animation)==manifest['animation_blend_sha256']
rebuild=json.loads((M/'reports/rebuild_check.json').read_text());assert rebuild['status']=='PASS'
contract=json.loads((HERE/'contract_changes.json').read_text())
evidence=dict(status='PASS',scope='Document-only rebuild; exact visible/source part geometry, transforms, materials, categories and display normals checked',
    original_source_blend_sha256=old_hash,current_source_blend_sha256=new_hash,
    complete_source_objects_compared=len(before),animation_actor_count=ac,changed_objects=changed,
    embedded_animation_source_differences=embedded_bad,source_geometry_signature=asig,
    video_and_animation_bytes_unchanged=True,geometry_input_unchanged=True,
    contract_changes='contract_changes.json',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    limits='Preserves existing evidence scope only. Does not resolve reaction initial assembly, harness, supplier interfaces, print strength or physical fit.')
(HERE/'source_equivalence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
contract['status']='PASS'
contract['status_scope']='Documentation synchronization and strict rebuild equivalence only'
contract['current_blend_sha256']=new_hash
contract['source_equivalence']='source_equivalence.json'
(HERE/'contract_changes.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
manifest.setdefault('rendered_source_blend_sha256',old_hash)
manifest['source_blend_sha256']=new_hash
manifest['source_equivalence_refresh']='studies/prearrival_finish/interface_sync/source_equivalence.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
delivery_path=M/'animation/delivery.json';delivery=json.loads(delivery_path.read_text())
delivery['source_blend_sha256']=new_hash
delivery['source_equivalence']='../studies/prearrival_finish/interface_sync/source_equivalence.json'
delivery['original_render_source_blend_sha256']=old_hash
delivery['published_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
delivery_path.write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
print('INTERFACE_EQUIVALENCE',len(before),'objects',ac,'actors',new_hash,flush=True)
