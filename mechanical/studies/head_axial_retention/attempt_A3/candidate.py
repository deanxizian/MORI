"""Independent head anti-lift study. Never saves source/config/STL/animation.
Only catalog boundary/abutment dimensions are documented; this is not bearing CAD.
"""
import sys,json,hashlib,math,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import replace_owned
from render import camera
load_collections();assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);sha=hashlib.sha256(source.read_bytes()).hexdigest()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
original={n:s.m for n,s in ss.items()}
def cylinder(r,z0,z1,x=0,y=0):return manifold.Manifold.cylinder(z1-z0,r,r,192).translate((x,y,z0))
def annulus(ro,ri,z0,z1):return cylinder(ro,z0,z1)-cylinder(ri,z0-.01,z1+.01)
def cube(a,b):return manifold.Manifold.cube(tuple(np.array(b)-a)).translate(a)
def hit(m,t,threshold=.01):
 a=np.array(m.bounding_box());b=np.array(t.bounding_box())
 if np.any(a[3:]<b[:3]) or np.any(b[3:]<a[:3]):return 0.
 v=max(0.,float((m^t).volume()));return v if v>threshold else 0.
def make(name,m,group='body',category='PRINTABLE',color=(.8,.47,.08)):
 d=m.to_mesh64();o=mesh(name,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist())
 o['role']='part';o['group']=group;o['category']=category;o['data_status']='ASSUMED';o['study_only']=True;o['export_candidate']=False
 mat=material('RETENTION_STUDY_'+name,color);o.data.materials.append(mat);return o
shift=-4.5
bz=D['yaw_bearing_z']+shift;bb=bz-3.5;bt=bz+3.5
# Independent alternative: lower the bearing/compact stops4.5mm; keep the
# servos, optics, head shell and all external datums unchanged. This tradeoff
# needs user approval. A4mm keeper with recessed heads stays below old rim.
collar=Solid(bpy.data.objects[PREFIX+'DATUM_Compact_Yaw_Collar']).m
key=Solid(bpy.data.objects[PREFIX+'DATUM_Compact_Yaw_Key']).m
fixedstops=[Solid(bpy.data.objects[PREFIX+'DATUM_Compact_Yaw_Fixed_'+str(i)]).m for i in [-1,1]]
yoke=(original['Pitch_Yoke']-annulus(20.1,9.7,161.29,163.71))+annulus(9.8,7.7,149,173.51)
yoke+=collar.translate((0,0,shift))+key.translate((0,0,shift))
yoke+=annulus(9.95,7.7,bb+.4,bt)+annulus(11,7.7,bt,bt+.85)
yoke+=manifold.Manifold.cylinder(.4,9.7,9.95,192).translate((0,0,bb))-cylinder(7.7,bb-.01,bb+.41)
# Remove old ledge and old stop cores; reconstruct actual outer-race support
# and a trial32.1mm housing bore. A broad ring provides blind insert backing.
base=original['Yaw_Base']
for m in fixedstops:base-=m
base-=cylinder(20.31,bt+.3,163.71)
base-=cylinder(15,147,bt+.31)
base+=annulus(27,16.05,bb,bt+.3)+annulus(27,15,147,bb)
base+=annulus(29.5,20.3,151.5,159.6)
base-=cylinder(16.05,bb,bt+.3)
base-=cylinder(29.3,159.6,163.71)
for m in fixedstops:base+=m.translate((0,0,shift))
keeper=annulus(29,12.45,159.6,163.6)-cube((-12.45,-40,159.5),(12.45,0,163.7))
fasteners={};axes=[(-11,23),(11,23)]
for i,(x,y) in enumerate(axes):
 keeper-=cylinder(1.7,159.5,163.7,x,y)
 keeper-=cylinder(3,161.9,163.7,x,y)
 base-=cylinder(2.025,153.6,159.7,x,y)
 screw=cylinder(1.45,153.9,161.9,x,y)+cylinder(2.85,161.9,163.55,x,y)
 screw-=cylinder(1,162.45,163.65,x,y)
 insert=cylinder(2.3,155.4,159.4,x,y)-cylinder(1.5,155.3,159.5,x,y)
 fasteners['Yaw_Keeper_Screw_'+str(i)]=screw
 fasteners['Yaw_Keeper_Insert_'+str(i)]=insert
bearing=original['Yaw_Bearing'].translate((0,0,shift))
replace_owned('Yaw_Bearing',bearing)
for n,m in [('Pitch_Yoke',yoke),('Yaw_Base',base)]:replace_owned(n,m)
ko=make('Yaw_Anti_Lift_Keeper',keeper);ko['functional_purpose']='Independent removable C plate blocks upward rotor withdrawal; nominal0.4mm running gap; not a bearing preload adjuster.'
for n,m in fasteners.items():
 o=make(n,m,category='PURCHASED_REFERENCE',color=(.45,.49,.55) if 'Screw' in n else (.68,.42,.12))
 o['reference']='Nominal M3x8 button-head / existing FINE SL-M3x4 envelope; no detailed thread fit'
# The bearing keeps its original annular envelope. Do not invent ball/race CAD.
bo=ss['Yaw_Bearing'].o;bo['candidate_product']='NSK6804ZZ';bo['source_url']='https://www.nsk.com/jp-ja/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6804zz-apn.html'
bo['model_fidelity']='BOUNDARY_ENVELOPE_ONLY';bo['data_status']='VENDOR_DOCUMENTED_BOUNDARY_AND_ABUTMENTS_ONLY'
geom=dict(original);geom.update(Pitch_Yoke=yoke,Yaw_Base=base,Yaw_Bearing=bearing,Yaw_Anti_Lift_Keeper=keeper);geom.update(fasteners)
changed=['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper']+list(fasteners)
allowed={frozenset(('Yaw_Base',n)) for n in fasteners if 'Insert' in n}
static=[]
for n in changed:
 for other,t in geom.items():
  if n==other or (other in changed and changed.index(other)<changed.index(n)) or frozenset((n,other)) in allowed:continue
  v=hit(geom[n],t)
  if v:static.append(dict(a=n,b=other,mm3=v))
print('STATIC',len(static),static[:4],flush=True)
# Scope: changed interfaces versus all bodies at130 combined nominal head poses.
fixed={n:m for n,m in geom.items() if n not in ss or ss[n].group not in ['yaw','pitch']}
moving={n:m for n,m in geom.items() if n in ss and ss[n].group in ['yaw','pitch']}
body_changed={'Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper'}|set(fasteners)
motion=[]
for yd in range(-60,61,10):
 for pd in range(-20,26,5):
  moved={n:m.transform(np.array(rigidtr(yd,pd if ss[n].group=='pitch' else 0))[:3,:]) for n,m in moving.items()}
  for n,m in moved.items():
   for other in (fixed if n=='Pitch_Yoke' else body_changed):
    v=hit(m,fixed[other])
    if v:motion.append(dict(yaw=yd,pitch=pd,a=n,b=other,mm3=v))
print('MOTION',len(motion),motion[:4],flush=True)
# Positive axial capture: journal can turn normally, but cannot lift out with
# plate fitted. This is hard-stop geometry, not a stiffness/strength calculation.
up=[]
for yd in range(-60,61,10):
 for dz in [.39,.41,1.0]:
  m=yoke.transform(np.array(rigidtr(yd,0))[:3,:]).translate((0,0,dz));v=hit(m,keeper)
  up.append(dict(yaw=yd,lift_mm=dz,overlap_mm3=v,expected='clear' if dz==.39 else 'blocked'))
# Bench-load C plate laterally before lowering it with the yaw subassembly.
bench=[]
bench_names={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output','Yaw_Reaction_Link','Yaw_Horn','Yaw_Lock_Screw'}
for dy in np.arange(0,60.01,.5):
 for n in bench_names:
  v=hit(keeper.translate((0,float(dy),0)),geom[n])
  if v:bench.append(dict(y_mm=float(dy),fixed=n,mm3=v))
# Install/remove keeper + yaw-only subassembly together after bridge and upper
# shell are in place; pitch cradle/head have not yet been installed.
yawset={n for n,s in ss.items() if s.group=='yaw'}|{'Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
fixture=set(geom)-yawset-{n for n,s in ss.items() if s.group=='pitch'}-set(fasteners)-{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
path=[]
# Existing yaw-only path is already checked; examine every new/changed piece
# against all relevant obstacles rather than certifying unselected horn parts.
for dz in np.arange(0,90.01,.5):
 for n in ['Pitch_Yoke','Yaw_Anti_Lift_Keeper']:
  for other in fixture:
   v=hit(geom[n].translate((0,0,float(dz))),geom[other])
   if v:path.append(dict(z_mm=float(dz),moving=n,fixed=other,mm3=v))
print('PATHS',len(bench),len(path),bench[:2],path[:2],flush=True)
# Long-leg2AF L-key, before pitch cradle/optics are installed. Nominal2AF
# handle envelope, all5deg orientations of the20mm transverse leg.
from interface_completion import axial
tool=[];screwin=[]
tool_fixture={n:m for n,m in geom.items() if n not in ss or ss[n].group!='pitch'}
for i,(x,y) in enumerate(axes):
 n='Yaw_Keeper_Screw_'+str(i);tf={k:v for k,v in tool_fixture.items() if k!=n}
 p=np.array([x,y,163.55]);a=np.array([0.,0,1.]);shapes=[axial(1.16,70,p+a*35.04,a)]
 for angle in range(0,360,5):
  t=math.radians(angle);b=np.array([math.cos(t),math.sin(t),0]);shapes.append(axial(1.16,20,p+a*(70-1.16)+b*10,b))
 for k,m in enumerate(shapes):
  for other,t in tf.items():
   v=hit(m,t)
   if v:tool.append(dict(screw=n,piece=k,other=other,mm3=v))
 for dz in np.arange(0,35.01,.5):
  for other,t in tf.items():
   v=hit(fasteners[n].translate((0,0,float(dz))),t)
   if v:screwin.append(dict(screw=n,z_mm=float(dz),other=other,mm3=v))
print('TOOLS',len(tool),len(screwin),tool[:2],screwin[:2],flush=True)
connect={n:len(geom[n].decompose()) for n in ['Pitch_Yoke','Yaw_Base','Yaw_Anti_Lift_Keeper']}
cap_ok=all((r['overlap_mm3']==0)==(r['expected']=='clear') for r in up)
status='PASS' if not any([static,motion,bench,path,tool,screwin]) and cap_ok and all(v==1 for v in connect.values()) else 'FAIL'
report=dict(status=status,scope='Independent NOMINAL geometry candidate only; not adopted. No print/strength/preload/complete drivetrain or harness qualification.',source=str(source),source_sha256=sha,blender_version=bpy.app.version_string,parameters=dict(bearing_candidate='NSK6804ZZ',bearing_d_D_B_mm=[20,32,7],documented_shaft_shoulder_d_mm=22,documented_housing_shoulder_D_max_mm=30,trial_journal_d_mm=19.9,trial_housing_bore_d_mm=32.1,bearing_z_change_mm=shift,keeper_OD_mm=58,keeper_thickness_mm=4,keeper_running_gap_mm=.4,screw_axes_xy_mm=axes,fasteners='2xM3x8 + 2xFINE SL-M3x4; existing catalog families, nominal only'),source_url=bo['source_url'],added_prints=1,added_standard_parts=4,changed_existing=['Pitch_Yoke','Yaw_Base','Yaw_Bearing'],static_hits=static,motion=dict(poses=130,hits=motion),capture=dict(status='PASS' if cap_ok else 'FAIL',samples=up),bench_plate_side_entry=dict(samples=121,hits=bench),paired_vertical_insertion=dict(samples=181,hits=path),tool_hits=tool,screw_entry_hits=screwin,connected_components=connect,limits=['C plate is an independent anti-lift stop with0.4mm nominal clearance, NOT zero-backlash bearing preload.','Bearing remains a boundary envelope: manufacturer race/seal CAD and actual PA12 fit still need verification.','Both19.9mm journal and32.1mm housing are nominal trial fits, not final PA12 tolerances; compensate by coupons.','SCS0009 horn/center screw/transmission and pitch short shafts remain BLOCKED by vendor evidence.','Current incomplete harness must be re-routed around the candidate ring; no cable qualification.','Standard screw envelope and insert interference are references, not detailed thread or heat-set strength verification.','User approval required before replacing main geometry.'])
(HERE/'candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
# Save editable independent candidate, with plain study colors and no production export.
for n,c in [('Pitch_Yoke',(.20,.43,.55)),('Yaw_Base',(.60,.64,.67)),('Yaw_Bearing',(.34,.39,.42))]:
 o=bpy.data.objects[PREFIX+n];o.data.materials.clear();o.data.materials.append(material('RETENTION_STUDY_'+n,c))
sc=bpy.context.scene;sc['study_status']=status;sc['not_adopted']=True;sc['source_sha256']=sha
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True;sc.display.shading.show_shadows=True;sc.display.shading.background_type='WORLD';sc.world.color=(.15,.17,.20)
sc.render.resolution_x=1100;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
shown={'Yaw_Base','Pitch_Yoke','Yaw_Bearing','Yaw_Anti_Lift_Keeper'}|set(fasteners)
for o in sc.objects:
 if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in shown;o.hide_set(o.hide_render)
for c in COLS.values():c.hide_render=False;c.hide_viewport=False
camera('head_retention',(130,190,250),(0,0,176),110)
sc.render.filepath=str(HERE/'candidate.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'candidate.blend'))
# Actual meridional sections for reviewer diagrams; display-only cross sections.
sections={}
for n in ['Pitch_Yoke','Yaw_Base','Yaw_Bearing','Yaw_Anti_Lift_Keeper']:
 sections[n]={'before':[a.tolist() for a in original[n].rotate((90,0,0)).slice(0).to_polygons()] if n in original else [],'after':[a.tolist() for a in geom[n].rotate((90,0,0)).slice(0).to_polygons()]}
(HERE/'sections.json').write_text(json.dumps(sections)+'\n')
print('CANDIDATE',status,'capture',cap_ok,'connected',connect,flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
