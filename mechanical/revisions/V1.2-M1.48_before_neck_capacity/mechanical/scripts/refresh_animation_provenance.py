"""Reuse an existing rendered animation only after exact source-geometry equivalence.

For a mechanical rebuild whose only change is reviewed hardware provenance.
Does not render, change keyframes or alter the video. Keeps the original render
source hash and records the verified relationship to the rebuilt master.
"""
import sys,hashlib,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from assembly_animation import signature

def originals(scene):
    return [o for o in scene.objects if o.type=='MESH' and o.get('mori_owner')==OWNER
            and o.get('role') in ['part','routing','display_content'] and o.get('group') not in ['dock','coupon']]

def mat_record(m):
    if not m:return None
    def value(v):
        if isinstance(v,(str,int,float,bool)) or v is None:return v
        try:return list(v)
        except TypeError:return str(type(v))
    return dict(name=m.name,color=list(m.diffuse_color),nodes=[dict(name=n.name,type=n.bl_idname,
        inputs=[(s.name,value(s.default_value)) for s in n.inputs if hasattr(s,'default_value')]) for n in m.node_tree.nodes] if m.use_nodes else [],
        links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.use_nodes else [])

def capture():
    scene=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=scene;load_collections();assembled()
    obs=originals(scene);rows={}
    for o in obs:
        h=hashlib.sha256();o.data.calc_loop_triangles()
        for a in [np.asarray(o.matrix_world,dtype=np.float64),np.asarray([v.co[:] for v in o.data.vertices],dtype=np.float32),np.asarray([t.vertices[:] for t in o.data.loop_triangles],dtype=np.int32),np.asarray([p.material_index for p in o.data.polygons],dtype=np.int32)]:h.update(a.tobytes())
        h.update(json.dumps([mat_record(s.material) for s in o.material_slots],sort_keys=True).encode())
        h.update(json.dumps({k:o.get(k) for k in ['category','group','role','data_status']},sort_keys=True).encode())
        rows[o.name]=h.hexdigest()
    return rows,signature(obs)

source=ROOT/'mori_v1_2.blend';animation=ROOT/'mori_assembly_animation.blend';manifest=ROOT/'animation/manifest.json'
m=json.loads(manifest.read_text());old_hash=m['source_blend_sha256'];new_hash=hashlib.sha256(source.read_bytes()).hexdigest()
assert old_hash!=new_hash,'No provenance refresh required'
bpy.ops.wm.open_mainfile(filepath=str(source));new,ns=capture()
bpy.ops.wm.open_mainfile(filepath=str(animation));old,os=capture()
assert old==new,'Source meshes/transforms/materials differ; regenerate animation instead'
assert ns==os==m['source_geometry_signature']
assert len(old)==m['actor_count']==180
video=ROOT/'animation/MORI_assembly.mp4';assert hashlib.sha256(video.read_bytes()).hexdigest()==m['video']['sha256']
assert new_hash==hashlib.sha256(source.read_bytes()).hexdigest()
evidence=dict(status='PASS_EXACT_SOURCE_EQUIVALENCE',revision=P['revision'],timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    original_render_source_blend_sha256=old_hash,current_source_blend_sha256=new_hash,source_geometry_signature=ns,
    actors_compared=len(old),mesh_triangles_transforms_materials_and_status_equal=True,animation_blend_unchanged=True,video_unchanged=True,
    reason='Hardware owner published P5R1 during rendering. Read-only provenance was reviewed and master rebuilt; no mechanical geometry or presentation content changed. The existing actual rendered frames remain valid.',
    limitation='This is source equivalence, not a new motion, strength or complete PCB fit qualification.')
save_json(ROOT/'animation/source_equivalence.json',evidence)
m.setdefault('rendered_source_blend_sha256',old_hash);m['source_blend_sha256']=new_hash;m['source_equivalence_refresh']='animation/source_equivalence.json'
save_json(manifest,m)
print('ANIMATION_SOURCE_EQUIVALENCE',len(old),'PASS')
