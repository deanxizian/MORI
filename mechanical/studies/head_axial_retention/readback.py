"""Validate saved candidate and make geometry-derived review sections."""
import sys,json,hashlib,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from render import camera
load_collections();assembled();bpy.context.view_layer.update()
report=json.loads((HERE/'candidate.json').read_text())
names=['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper']+['Yaw_Keeper_'+k+'_'+str(i) for k in ['Screw','Insert'] for i in range(2)]
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in names}
capture=[];stops=[]
for yd in range(-60,61,10):
 for dz in [0,.39,.41]:
  m=ss['Pitch_Yoke'].m.transform(np.array(rigidtr(yd,0))[:3,:]).translate((0,0,dz));v=max(0,(m^ss['Yaw_Anti_Lift_Keeper'].m).volume());capture.append(dict(yaw=yd,lift_mm=dz,volume_mm3=v))
for sign in [-1,1]:
 first=None
 for yd in np.arange(60,66.01,.25):
  m=ss['Pitch_Yoke'].m.transform(np.array(rigidtr(sign*yd,0))[:3,:]);v=max(0,(m^ss['Yaw_Base'].m).volume())
  if v>.01:first=dict(yaw_deg=sign*float(yd),overlap_mm3=float(v));break
 stops.append(first)
sections=json.loads((HERE/'sections.json').read_text())
for n,s in ss.items():
 sections.setdefault(n,{'before':[]})['after']=[p.tolist() for p in s.m.rotate((90,0,0)).slice(0).to_polygons()]
(HERE/'sections.json').write_text(json.dumps(sections)+'\n')
# Check nominal contact area on only the supplier-documented annular abutment
# regions, not a fabricated bearing race model.
ann=lambda ro,ri,z0,z1:manifold.Manifold.cylinder(z1-z0,ro,ro,192).translate((0,0,z0))-manifold.Manifold.cylinder(z1-z0+.02,ri,ri,192).translate((0,0,z0-.01))
areas=dict(rotor_shoulder_mm2=float((ss['Pitch_Yoke'].m^ann(11,10.3,156,156.01)).volume()/.01),housing_outer_ring_mm2=float((ss['Yaw_Base'].m^ann(15.7,15,148.99,149)).volume()/.01))
checks=dict(status='PASS' if all((r['volume_mm3']>.01)==(r['lift_mm']==.41) for r in capture) and all(r and 64<=abs(r['yaw_deg'])<=64.5 for r in stops) and min(areas.values())>30 else 'FAIL',source_candidate_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),blender_version=bpy.app.version_string,capture=capture,mechanical_stop_onsets=stops,nominal_abutment_contact_areas=areas,connected_components={n:len(s.m.decompose()) for n,s in ss.items() if n in ['Pitch_Yoke','Yaw_Base','Yaw_Anti_Lift_Keeper']},clearance_mm=.4,limits='Nominal shape readback only; no bearing preload, actual fit, strength or drive coupling verification.')
(HERE/'readback.json').write_text(json.dumps(checks,indent=2)+'\n')
print('READBACK',checks['status'],stops,areas,flush=True)
# Render a cropped, sectioned copy; no save and no production output.
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.hide_render=True
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_cavity=False;sc.display.shading.show_shadows=True;sc.display.shading.show_specular_highlight=False
sc.render.resolution_x=1100;sc.render.resolution_y=760;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
clip=manifold.Manifold.cube((100,50,34)).translate((-50,-50,145))
colors={'Pitch_Yoke':(.10,.38,.55),'Yaw_Base':(.62,.67,.69),'Yaw_Bearing':(.37,.29,.55),'Yaw_Anti_Lift_Keeper':(.95,.59,.10)}
for n,s in ss.items():
 m=s.m^clip
 if m.is_empty():continue
 d=m.to_mesh64();o=mesh('RETENTION_VIEW_'+n,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist());o['role']='presentation_section';o['export_candidate']=False
 o.data.materials.append(material('RETENTION_VIEW_'+n,colors.get(n,(.30,.32,.36) if 'Screw' in n else (.65,.43,.16))))
camera('head_retention_section',(100,160,217),(0,-2,159),91)
sc.render.filepath=str(HERE/'section.png');bpy.ops.render.render(write_still=True)
