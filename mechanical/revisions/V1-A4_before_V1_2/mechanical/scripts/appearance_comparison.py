"""Render the preserved baseline under current studio lights and the same review camera."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly']
lights={o.name:dict(location=list(o.location),rotation=list(o.rotation_euler),energy=o.data.energy,size=o.data.size) for o in bpy.context.scene.objects if o.type=='LIGHT'}
view=next(v for v in json.loads((ROOT/'reports/render_manifest.json').read_text()) if v['view']=='45_assembled')
baseline=ROOT/P['wheel_inset_revision']['baseline_model']
if not baseline.exists():raise RuntimeError('Preserved baseline is required for a truthful before/after comparison')
bpy.ops.wm.open_mainfile(filepath=str(baseline));bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for name,p in lights.items():
 o=bpy.data.objects[name];o.location=p['location'];o.rotation_euler=p['rotation'];o.data.energy=p['energy'];o.data.size=p['size']
camera('before_refinement',view['camera_mm'],view['target_mm'],view['ortho_scale_mm'])
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=view['samples'];sc.cycles.use_denoising=True
sc.render.resolution_x=view['resolution'];sc.render.resolution_y=view['resolution'];sc.render.resolution_percentage=100
sc.render.filepath=str(ROOT/'renders/before_refinement.png');bpy.ops.render.render(write_still=True)
save_json(ROOT/'reports/appearance_comparison.json',{'baseline_model':str(baseline.relative_to(ROOT)),'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'camera_matches_current':True,'studio_lights_match_current':True,'scope':P['wheel_inset_revision']['baseline_revision']+' vs '+P['revision']+'. Actual preserved geometry/materials; same studio lights and camera; no image generation.'})
print('APPEARANCE_COMPARISON_COMPLETE',flush=True)
