"""Read-only review frames from the saved animation; never saves the blend."""
import bpy,json
from pathlib import Path
out=Path(__file__).resolve().parent
m=json.loads((out/'manifest.json').read_text())
s=bpy.data.scenes['MORI_Assembly_Animation'];bpy.context.window.scene=s
s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG'
frames={
 'body_start':next(a['start'] for a in m['stages'] if a['source_step']==19),
 'bridge_seating':next(a['start'] for a in m['stages'] if a['source_step']==8)+25,
 'pitch_entry':next(a['start'] for a in m['stages'] if a['source_step']==11)+26,
}
for name,frame in frames.items():
 s.frame_set(frame);s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
(out/'review_frames.json').write_text(json.dumps(frames,indent=2)+'\n')
