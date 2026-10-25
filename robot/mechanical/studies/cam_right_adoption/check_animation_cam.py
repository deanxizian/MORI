"""Read the actual animation matrices for CAM installation, including bench root."""
from pathlib import Path
import sys,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from validate_cam_right_services import hits
from assembly_animation import AP,SCENE_NAME
source=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=source
load_collections()
for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
assembled()
bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in source.objects if o.type=='MESH' and o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
inverse={n:s.o.matrix_world.inverted() for n,s in ss.items()}
scene=bpy.data.scenes[SCENE_NAME];bpy.context.window.scene=scene
manifest=json.loads((ROOT/'animation/manifest.json').read_text())
stage=next(s for s in manifest['stages'] if s.get('source_step',s['index'])==12)
actors={o.name.removeprefix(AP):o for o in scene.objects if o.get('presentation_actor')}
moving=P['cam_orientation']['changed_existing_ids'];rows=[];checked=0
for frame in np.arange(stage['start'],stage['end']+.01,.5):
    scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update()
    visible={n:o for n,o in actors.items() if not o.hide_render and n in ss}
    def at(n):return ss[n].m.transform(np.asarray(actors[n].matrix_world@inverse[n])[:3,:])
    fixed={n:at(n) for n in visible if n not in moving}
    for n in moving:
        if n not in visible:continue
        checked+=1
        rows.extend(dict(frame=float(frame),moving=n,**row) for row in hits(at(n),fixed,tol=.001))
    if len(rows)>20:break
result=dict(status='PASS' if not rows else 'FAIL',revision=P['revision'],stage=stage,
    sampled_actor_poses=checked,hits=rows,source_blend_sha256=manifest['source_blend_sha256'],
    animation_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    method='Saved animation transforms every half frame, including Head_Bench motion, against every visible native part. Real plug and flexible wiring omitted.',
    continuous_collision='NOT_TESTED',manufacturing_release=False)
save_json(HERE/'animation_cam_readback.json',result)
print('CAM_ANIMATION_READBACK',result['status'],checked,rows[:3],flush=True)
if rows:raise RuntimeError('CAM animation path has native interference')
