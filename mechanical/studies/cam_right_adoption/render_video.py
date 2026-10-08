"""Render to a unique temporary path before replacing the published MP4."""
from pathlib import Path
import bpy,hashlib,json,uuid
ROOT=Path(__file__).resolve().parents[2]
scene=bpy.data.scenes['MORI_Assembly_Animation'];bpy.context.window.scene=scene
report=json.loads((ROOT/'animation/manifest.json').read_text())
source=ROOT/'mori_v1_2.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)==report['source_blend_sha256'] and report['revision']=='V1.2-M1.54'
target=ROOT/'animation/MORI_assembly.mp4';pending=target.with_name('.M1_54_render_'+uuid.uuid4().hex+'.mp4')
scene.render.filepath=str(pending)
try:
    bpy.ops.render.render(animation=True)
    assert pending.exists() and pending.stat().st_size>100000
    pending.replace(target)
finally:pending.unlink(missing_ok=True)
assert sha(source)==report['source_blend_sha256']
print('M1_54_VIDEO_RENDERED',target.stat().st_size,flush=True)
