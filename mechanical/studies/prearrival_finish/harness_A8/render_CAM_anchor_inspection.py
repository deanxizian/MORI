"""Inspect the independent CAM anchor; writes study images only."""
from pathlib import Path
import sys
SCRIPT = Path(__file__).resolve(); A8 = SCRIPT.parent
sys.path.insert(0, str(A8.parents[3] / 'mechanical/scripts'))
from common import *
from render import camera

dest = A8 / 'cam_anchors/candidate'
assert Path(bpy.data.filepath) == dest / 'candidate.blend'
load_collections(); assembled(); bpy.context.view_layer.update()
visible = {'Pitch_Yoke', 'Pitch_Servo', 'Pitch_Output', 'Pitch_Bearing_L',
           'Head_Pitch_Ear_0_Screw', 'Head_Pitch_Ear_0_Nut'}
for collection in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:
    COLS[collection].hide_render = True
for o in bpy.context.scene.objects:
    if o.type in ['MESH', 'CURVE']:
        o.hide_render = (o.name.removeprefix(PREFIX) not in visible
                        and not o.name.startswith('A8_CAM_Tie_'))
addition = np.load(dest / 'addition.npz')
mesh = bpy.data.meshes.new('A8_CAM_ADDITION_HIGHLIGHT')
mesh.from_pydata(addition['vertices_mm'].tolist(), [], addition['triangles'].tolist()); mesh.update()
obj = bpy.data.objects.new('A8_CAM_ADDITION_HIGHLIGHT', mesh)
bpy.context.scene.collection.objects.link(obj)
mesh.materials.append(material('A8_SUPPORT_CYAN', (.02,.47,.62), roughness=.7))
# Slightly offset the highlight only for presentation, and state it in output.
obj.location = (0, 0, .002)
sc = bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for name, eye, target, scale in [
    ('front_detail', (26,65,270), (-18,-2,229), 50),
    ('rear_detail', (20,-80,270), (-18,-2,231), 50),
    ('root_detail', (-10,-35,244), (-29,-2,234), 20)]:
    camera(name, eye, target, scale)
    sc.render.filepath=str(dest/(name+'.png'));bpy.ops.render.render(write_still=True)
print('INSPECTION_RENDER_DONE', flush=True)
