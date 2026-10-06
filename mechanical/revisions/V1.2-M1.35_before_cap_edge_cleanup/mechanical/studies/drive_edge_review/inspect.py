"""Read current assembly and locate the cap's narrow underside transition.

Only diagnostic renders/measurements are written; source geometry is not saved.
"""
import sys, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from render import camera

out=Path(__file__).parent
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled()
ids=['Drive_Bridge','Motor_Retainer','Wheel_Bearing_R_Inner','Wheel_Bearing_R_Outer']
solids={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids}
q=P['drive_print_cleanup'];hx=q['central_outer_xy_mm'][0]/2
lo=[hx,-q['bearing_bar_depth_mm']/2,q['bearing_bar_bottom_inner_z_mm']]
hi=[q['bearing_bar_bottom_transition_x_mm'],q['bearing_bar_depth_mm']/2,q['bearing_bar_bottom_outer_z_mm']]
region=manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
piece=solids['Motor_Retainer'].m^region
result={'revision':P['revision'],'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        'inspected_region_xyz_mm':list(zip(lo,hi)),'cap_region_volume_mm3':piece.volume(),
        'drive_region_volume_mm3':(solids['Drive_Bridge'].m^region).volume(),
        'gap_to_bearings_mm':{n:piece.min_gap(solids[n].m,30) for n in ids if 'Bearing' in n},
        'source_saved':False,'geometry_changed':False,'strength':'NOT_TESTED',
        'reason':'Transition between cap half-width33.5, saddle underside step at35, and underside elevations42/44.3.'}
trial=solids['Motor_Retainer'].m-region
result['read_only_trim_probe']={'removed_volume_mm3':solids['Motor_Retainer'].m.volume()-trial.volume(),
                               'remaining_connected_bodies':len(trial.decompose()),
                               'manifold_status':str(trial.status()),
                               'applied_to_model':False,
                               'strength_and_creep':'NOT_TESTED; no structural safety claim from connected geometry.'}
save_json(out/'inspection.json',result)
if '--measure-only' in sys.argv:
 print('DRIVE_EDGE_INSPECTED',result,flush=True)
 raise SystemExit(0)
sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1000;sc.render.resolution_y=800;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for n in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[n].hide_render=True
for name,color in [('Drive_Bridge',(.64,.66,.65)),('Motor_Retainer',(.22,.36,.41))]:
 o=bpy.data.objects[PREFIX+name];o.data.materials.clear();o.data.materials.append(material('edge_review_'+name,color,roughness=.7))
sets={'underside':({'Drive_Bridge','Motor_Retainer'},(120,300,-205),(20,0,46),103),
      'cap_close':({'Motor_Retainer'},(120,150,-150),(35,0,44),46)}
for name,(visible,loc,aim,scale) in sets.items():
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
 camera('edge_review_'+name,loc,aim,scale);sc.render.filepath=str(out/(name+'.png'))
 bpy.ops.render.render(write_still=True)
print('DRIVE_EDGE_INSPECTED',result,flush=True)
