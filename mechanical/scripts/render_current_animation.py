"""Render a verified editable animation to fresh technical-review media."""
import sys,json,hashlib,uuid,argparse
from pathlib import Path
import bpy

root=Path(__file__).resolve().parents[1];out=root/'animation'
parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['stills','video'],required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
m=json.loads((out/'manifest.json').read_text());v=json.loads((out/'validation.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert v['status']=='PASS' and sha(root/'mori_v1_2.blend')==m['source_blend_sha256']
assert sha(bpy.data.filepath)==m['animation_blend_sha256']
scene=bpy.data.scenes['MORI_Assembly_Animation'];bpy.context.window.scene=scene
scene.render.engine='BLENDER_WORKBENCH';scene.display.render_aa='8'
sh=scene.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=False
sh.background_type='VIEWPORT';sh.background_color=(.022,.030,.041)
# Workbench does not use the emission shader used by the native Eevee titles.
# Give these presentation-only fonts a legible material; source meshes untouched.
for o in scene.objects:
    if o.type=='FONT':
        for mat in o.data.materials:mat.diffuse_color=(.96,.98,1.,1.)
if args.kind=='stills':
    scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
    for s in m['stages']:
        scene.frame_set(s['end']);scene.render.filepath=str(out/f'step_{s["index"]:02d}.png')
        bpy.ops.render.render(write_still=True)
else:
    target=out/'MORI_assembly.mp4';temp=out/('.render-'+uuid.uuid4().hex+'.mp4')
    scene.render.image_settings.media_type='VIDEO';scene.render.image_settings.file_format='FFMPEG'
    scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264';scene.render.ffmpeg.constant_rate_factor='MEDIUM'
    scene.render.filepath=str(temp)
    try:
        scene.frame_set(1);bpy.ops.render.render(animation=True)
        assert temp.exists() and temp.stat().st_size>100000
        temp.replace(target)
    finally:temp.unlink(missing_ok=True)
    m['rendered_video']=True;m['video']={'file':'MORI_assembly.mp4','bytes':target.stat().st_size,'sha256':sha(target)}
m['render_engine']='BLENDER_WORKBENCH technical review';m['render_script_sha256']=sha(__file__)
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
assert sha(root/'mori_v1_2.blend')==m['source_blend_sha256']
print('CURRENT_ANIMATION_RENDERED',args.kind,flush=True)
