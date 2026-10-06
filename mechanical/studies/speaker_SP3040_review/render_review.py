"""Actual SP3040 shell mounting; no geometry modifications for illustration."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from render import camera
from speaker_geometry import speaker_transform
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc
load_collections();assembled();out=Path(__file__).parent
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1100;sc.render.resolution_y=850;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';tr=speaker_transform();origin=tr@Vector((0,0,0))
speaker={n for n in ['Speaker','Speaker_Gasket','Speaker_Screw_-1','Speaker_Screw_1','Speaker_Insert_-1','Speaker_Insert_1']}
views={
 'speaker_front':({'Speaker'},(90,175,90),(0,-4,0),81),
 'speaker_side':(speaker,(140,-80,45),(0,-3,0),81),
 'shell_seats':({'Body_Upper'},(70,-130,-180),(0,-2,0),112),
 'shell_mounted':(speaker|{'Body_Upper'},(70,-130,-180),(0,-4,0),112),
}
manifest={}
for name,(show,offset,aim,scale) in views.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in show
 for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[n].hide_render=True
 loc=tr@Vector(offset);target=tr@Vector(aim)
 camera('sp3040_'+name,loc,target,scale);sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 manifest[name]={'file':name+'.png','sha256':hashlib.sha256(Path(sc.render.filepath).read_bytes()).hexdigest(),'camera_mm':list(loc),'aim_mm':list(target),'scale_mm':scale}
save_json(out/'render_manifest.json',{'revision':P['revision'],'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'geometry_changed_for_render':False,'views':manifest})
print('SP3040_VIEWS_COMPLETE')
