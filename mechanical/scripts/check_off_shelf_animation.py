"""Read actual saved UPS assembly frames with already-installed fixtures."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from assembly_animation import AP
source=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=source;load_collections()
for c in COLS.values():c.hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
base={n:s.o.matrix_world.copy() for n,s in ss.items()}
scene=bpy.data.scenes['MORI_Assembly_Animation'];bpy.context.window.scene=scene
m=json.loads((ROOT/'animation/manifest.json').read_text());stage=next(s for s in m['stages'] if s['source_step']==9)
actors={n:bpy.data.objects[AP+n] for n in ss};moving={'UPS_Module'}|{n for n in ss if n.startswith('UPS_Direct_')}
bad=[];count=0
for frame in np.arange(stage['start'],stage['end']+.01,.5):
    scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update();count+=1
    visible={n for n,o in actors.items() if not o.hide_render};world={}
    for n in visible:
        world[n]=ss[n].m.transform(np.array(actors[n].matrix_world@base[n].inverted())[:3,:])
    for n in moving&visible:
        a=world[n];ab=np.array(a.bounding_box())
        for other,b in world.items():
            if other==n:continue
            bb=np.array(b.bounding_box())
            if np.any(ab[3:]<bb[:3]) or np.any(bb[3:]<ab[:3]):continue
            volume=float((a^b).volume())
            if volume>.05:bad.append(dict(frame=float(frame),moving=n,target=other,volume_mm3=volume))
    if len(bad)>20:break
result=dict(status='FAIL' if bad else 'PASS',revision=P['revision'],source_blend_sha256=m['source_blend_sha256'],
 animation_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),samples=count,hits=bad,
 scope='UPS approach 0.5mm below seating plane, rise into seats, four screws then four nuts. Actual saved actor transforms sampled every half frame, with visible current rigid fixtures.',
 hands_and_flexible_wires='NOT_TESTED',manufacturing_release=False)
save_json(ROOT/'animation/off_shelf_path_validation.json',result)
assert result['status']=='PASS',bad[:3]
print('UPS_ANIMATION_PATH_PASS',count,flush=True)
