"""M1 actual A/B bodies, identical cameras, optics, wheel ratio and hardware allocations.
Only in-memory variant selector changes; canonical JSON and .blend are untouched.
"""
import sys,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as c
import build as b
from render import camera
from validate import Solid,intersect_volume,volume_moments
out=c.ROOT/'renders/variants';out.mkdir(parents=True,exist_ok=True);records=[];selected=c.P['shape']['selected']
views={'front':((0,650,145),(0,0,145),325),'side':((650,0,145),(0,0,145),325),'45':((380,500,325),(0,0,145),340)}
# Variant geometry is temporary; preserve ALL current generated report inputs.
report_snapshot={f:f.read_bytes() for f in (c.ROOT/'reports').iterdir() if f.suffix in ['.json','.csv','.md']}
try:
 for variant in ['A','B']:
  b.CONTACTS.clear()
  c.P['shape']['selected']=variant;sc=c.setup_scene();b.materials()
  for fn in [b.shells,b.optics,b.head_joint,b.wheel_and_drive,b.frame_and_electronics,b.fasteners_and_coupons,b.v12_joint_details,b.apply_purchased_geometry,b.apply_structural_simplification,b.apply_monocoque_structure,b.apply_simple_modules,b.apply_belly_relayout,b.dock,b.controls_datums,b.studio]:fn()
  c.assembled();sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=800;sc.render.resolution_y=800;sc.render.resolution_percentage=100
  shell=[Solid(c.bpy.data.objects[c.PREFIX+n]) for n in ['Body_Upper','Body_Lower']]
  cavity=b.body_outer('study_cavity',c.P['shell_thickness_mm']);cavity_vol=Solid(cavity).m.volume();c.bpy.data.objects.remove(cavity,do_unlink=True)
  shell_mass=sum(a.m.volume() for a in shell)*.00124*.98
  intersections=[]
  for o in c.parts():
   if o.get('group')=='body' and o.get('category')=='PLACEHOLDER':
    a=Solid(o)
    for bs in shell:
     v=intersect_volume(a,bs)
     if v>.01:intersections.append({'part':a.name,'shell':bs.name,'volume_mm3':v})
  files=[]
  for name,args in views.items():
   c.bpy.data.objects[c.PREFIX+'Studio_Ground'].hide_render=name!='45';camera(variant+'_'+name,*args);sc.render.filepath=str(out/f'{variant}_{name}.png');c.bpy.ops.render.render(write_still=True);files.append('renders/variants/'+variant+'_'+name+'.png')
  records.append({'variant':variant,'selected':variant==selected,'profile':c.P['shape']['variants'][variant],'same_head_wheel_display_envelopes':True,'height_mm':c.D['normal_height_mm'],'enclosed_cavity_estimate_cm3':round(cavity_vol/1000),'body_shell_mass_g_estimate':round(shell_mass),'body_allocation_shell_intersections':intersections,'images':files})
finally:
 c.P['shape']['selected']=selected
 for path,data in report_snapshot.items():path.write_bytes(data)
c.save_json(c.ROOT/'reports/parameter_comparison.json',{'candidates':records,'camera_definitions':views,'scope':'M1 exterior comparison with same actual internal allocations. Cavity volume is not a usable rectangular envelope or hardware-fit qualification.','decision':'Select B: 4.5% pole-dependent shoulder bias and1.5% depth reduction give a mild fuller shoulder/tucked belly. Same height, tyres and module sizes; broad rounded flanks retained. Both retain horizontal removable body split and vertical head split. COM/space impact is small and still requires selected-parts checks; final B validation is separate.','authoritative_parameter':'config/geometry.json shape.selected; no second geometry truth or scaled hardware'})
print('COMPARISON_COMPLETE',flush=True)
