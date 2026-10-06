"""Actual final model views; temporary cuts/color overrides are not saved."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from render import camera
load_collections();assembled();sc=bpy.context.scene
out=ROOT/'studies/head_axial_retention/adopted';out.mkdir(exist_ok=True)
names=P['head_axial_retention']['changed_existing_ids']+P['head_axial_retention']['new_ids']
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in names}
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.show_specular_highlight=False;sc.display.shading.background_type='WORLD';sc.world.color=(.20,.23,.27)
sc.render.resolution_x=1100;sc.render.resolution_y=760;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
for c in COLS.values():c.hide_render=False;c.hide_viewport=False
for o in sc.objects:
 if o.type=='MESH':o.hide_render=True
colors={'Pitch_Yoke':(.10,.38,.55),'Yaw_Base':(.62,.67,.69),'Yaw_Bearing':(.37,.29,.55),'Yaw_Anti_Lift_Keeper':(.95,.59,.10)}
clip=manifold.Manifold.cube((100,50,34)).translate((-50,-50,145))
for view in ['section','assembly','keeper']:
 shown=[]
 for n,s in ss.items():
  if view=='keeper' and n!='Yaw_Anti_Lift_Keeper':continue
  m=s.m^clip if view=='section' else s.m
  if m.is_empty():continue
  d=m.to_mesh64();o=mesh('RETENTION_FINAL_VIEW_'+n,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist());o['role']='presentation_section';o['export_candidate']=False
  o.data.materials.append(material('RETENTION_FINAL_'+n,colors.get(n,(.30,.32,.36) if 'Screw' in n else (.65,.43,.16))))
  shown.append(o)
 if view=='section':camera('retention_final_section',(100,160,217),(0,-2,159),91)
 elif view=='keeper':camera('retention_final_keeper',(80,-140,270),(0,0,161),88)
 else:camera('retention_final_assembly',(130,190,290),(0,0,180),140)
 sc.render.filepath=str(out/(view+'.png'));bpy.ops.render.render(write_still=True)
 for o in shown:bpy.data.objects.remove(o,do_unlink=True)
save_json(out/'manifest.json',{'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'revision':P['revision'],'views':['section.png','assembly.png','keeper.png'],'temporary_materials_and_sections_only':True})
