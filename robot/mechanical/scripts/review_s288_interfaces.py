"""M1.14 actual-model wheel-interface views; no changes to the saved assembly."""
import sys,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera,line,textlabel
OUT=ROOT/'studies/s288_interface_review';OUT.mkdir(parents=True,exist_ok=True)
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest();sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
validation=json.loads((ROOT/'reports/wheel_interface_validation.json').read_text());assert validation['status']=='PASS_GEOMETRY_ONLY'
w=P['wheel_interface'];wz=D['wheel_z'];original={o.name:(o.location.copy(),list(o.data.materials) if o.type=='MESH' else []) for o in sc.objects}
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.image_settings.file_format='PNG';sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
for c in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[c].hide_render=True
for c in ['PRINTABLE','PLACEHOLDER','PURCHASED_REFERENCE','ANNOTATIONS']:COLS[c].hide_viewport=False;COLS[c].hide_render=False
material('annotation',(.12,.82,.97),emission=.5);material('review_shaft',(.06,.38,.52),metallic=.55);material('review_bearing',(.62,.47,.17),metallic=.6);material('review_plastic',(.13,.15,.16),roughness=.58)
def ob(n):return bpy.data.objects[PREFIX+n]
for o in parts():
 n=o.name.removeprefix(PREFIX)
 if n.startswith('Wheel_Axle'):o.data.materials.clear();o.data.materials.append(MATS['review_shaft'])
 if n.startswith('Wheel_Bearing'):o.data.materials.clear();o.data.materials.append(MATS['review_bearing'])
 if n.startswith('Drive_Motor'):o.data.materials.clear();o.data.materials.append(MATS['review_plastic'])
def show(visible):
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
  if o.name in original:o.location=original[o.name][0]
def label(name,txt,loc,size,cam):
 o=textlabel(name,txt,loc,size);o.rotation_euler=cam.rotation_euler.copy();return o
def clear():
 for o in list(COLS['ANNOTATIONS'].objects):
  if o.get('mori_owner')==OWNER:bpy.data.objects.remove(o,do_unlink=True)
def render(name):
 sc.render.filepath=str(OUT/(name+'.png'));bpy.context.view_layer.update();bpy.ops.render.render(write_still=True);clear()
right={n for n in [o.name.removeprefix(PREFIX) for o in parts()] if n.endswith('_R') or n.startswith(('Wheel_Bearing_R_','Wheel_Spacer_R_','Wheel_Output_Screw_R_','S288_Output_R_'))}
right={n for n in right if n.startswith(('Drive_Motor','S288_Output','Wheel_','Tire_'))}
show(right);cam=camera('review_cartridge',(170,-260,165),(42,0,57),200)
label('cartridge_title','S288 / METAL FLANGE SHAFT / DOUBLE-D HUB',(40,-4,117),4.5,cam)
label('cartridge_note','BLUE: CUSTOM STEEL    GOLD: 686ZZ    SUPPORTS HIDDEN',(40,-4,110),2.65,cam)
render('drive_axis')
# Actual through-axis section; central hub strip, not a second wheel geometry.
show(set());crops=[]
for n in sorted(right-{'Tire_R'}|{'Drive_Bridge','Motor_Retainer'}):
 src=ob(n);cp=clone(src,'review_section_'+n)
 zspan=22 if n=='Wheel_Hub_R' else 52
 intersect(cp,box('section_half',(42.5,40,wz),(81,80,zspan)))
 cp.data.materials.clear()
 for m in src.data.materials:cp.data.materials.append(m)
 cp.hide_render=False;crops.append(cp)
cam=camera('review_section',(42,-400,wz),(42,0,wz),100)
for x in range(-4,85,4):line('axis',(x,-24,wz),(x+2,-24,wz),.08)
label('section_title','ACTUAL AXIAL SECTION / RIGHT DRIVE',(41,-24,82),3.1,cam)
for letter,x,z,tx,tz in [('A',12,74,12,62),('B',25.5,71,25.5,59),('C',44,76,43,55),('D',38,29,38,46),('D2',48,29,48,46),('E',57,35,56,49),('F',68,75,68,61),('G',78,33,75,53)]:
 label('key_'+letter,letter,(x,-24,z),3.2,cam);line('leader',(x,-23,z-1 if z>60 else z+3),(tx,-23,tz),.065)
label('section_legend','A CASE   B OUTPUT   C ONE-PIECE SHAFT   D 686ZZ   E SPACER   F D-HUB   G M3',(41,-24,22),1.7,cam)
render('axial_section')
for o in crops:SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
# Only display offsets move the two printed seats. Shafts remain assembled.
visible={'Drive_Bridge','Motor_Retainer'}|{o.name.removeprefix(PREFIX) for o in parts() if o.name.removeprefix(PREFIX).startswith(('Drive_Motor_','S288_Output_','Wheel_Axle_','Wheel_Bearing_','Wheel_Output_Screw_','Wheel_Cap_Clamp_','Motor_Top_Pad_','Motor_Retainer_Pad_'))}
show(visible);ob('Drive_Bridge').location.z+=26;ob('Motor_Retainer').location.z-=22
for i in range(4):ob('Wheel_Cap_Clamp_Screw_'+str(i)).location.z-=22;ob('Wheel_Cap_Clamp_Nut_'+str(i)).location.z+=26
cam=camera('review_split',(-195,-280,190),(0,0,56),185)
label('split_title','ONE SHARED CAGE + ONE REMOVABLE CAP',(0,-10,123),5,cam)
label('split_note','EXPLODED DISPLAY ONLY / FOUR M3 CAP BOLTS',(0,-10,115),3.2,cam)
render('split_seat')
show(set());crops=[]
for n in ['Wheel_Hub_R','Wheel_Axle_R','Wheel_End_Screw_R','Wheel_End_Washer_R','Wheel_Spacer_R_1']:
 src=ob(n);cp=clone(src,'review_hub_'+n);intersect(cp,box('hub_crop',(66,8,wz),(34,20,25)))
 cp.data.materials.clear()
 for m in src.data.materials:cp.data.materials.append(m)
 cp.hide_render=False;crops.append(cp)
cam=camera('review_hub',(138,-190,122),(66,0,53),70)
label('hub_title','DOUBLE-D / 12.2 mm ENGAGEMENT',(65,-1,72),1.65,cam)
label('hub_note','M3 END SCREW + WASHER / ACTUAL CUTAWAY',(65,-1,32),1.35,cam)
render('hub_lock')
for o in crops:SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
show({'Body_Lower','Load_Frame','Drive_Bridge','Motor_Retainer','Wheel_Axle_L','Wheel_Axle_R','Drive_Motor_L','Drive_Motor_R'})
ob('Body_Lower').location.z-=22
cam=camera('review_service',(260,350,205),(0,0,86),227)
label('service_title','LOWER SHELL DESCENDS / SHAFTS STAY IN PLACE',(0,0,156),4.3,cam)
label('service_note','WHEELS + OUTER SPACERS REMOVED FIRST',(0,0,147),3.2,cam)
render('shell_service')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
out={'revision':P['revision'],'status':validation['status'],'source_blend':str(source),'source_sha256':source_hash,'source_is_unchanged':True,'dimensions_from':'config/geometry.json#/wheel_interface','validation':'mechanical/reports/wheel_interface_validation.json','views':['drive_axis','axial_section','split_seat','hub_lock','shell_service'],'no_generative_images':True,'section_method':'Clipped copies of assembled solids; display explosion and shell-removal offset never used in exported STL','physical_qualification':False}
save_json(OUT/'inspection.json',out)
print('S288_DESIGN_REVIEW_RENDERED')
