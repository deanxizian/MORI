"""Verify the proposed0.2mm paired axis move and0.2mm keeper/rim enlargement."""
from pathlib import Path
import sys,json,math,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,manifold,sha
from validate import rigidtr
from interface_completion import axial
from neck_capacity import cylinder
ctx=Context();start=time.time();original={n:s.m for n,s in ctx.ss.items()};geom=original.copy()
ids=['Yaw_Base','Yaw_Anti_Lift_Keeper','Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1']
for n in ids:
 d=np.load(HERE/('round_'+n+'.npz'));geom[n]=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
for n,r in ctx.targets.items():
 if n not in geom:geom[n]=r['m']
group={n:s.group for n,s in ctx.ss.items()}
def rotate(m,yaw,pitch=0):return m.transform(np.asarray(rigidtr(yaw,pitch))[:3,:])
def hit(m,t):
 a=np.asarray(m.bounding_box());b=np.asarray(t.bounding_box())
 if np.any(a[3:]<=b[:3]) or np.any(b[3:]<=a[:3]):return 0.
 v=float((m^t).volume());return v if v>.01 else 0.
allowed={frozenset(('Yaw_Base','Yaw_Keeper_Insert_'+str(i))) for i in range(2)}
static=[]
for i,n in enumerate(ids):
 for other,t in geom.items():
  if n==other or (other in ids and ids.index(other)<i) or frozenset((n,other)) in allowed:continue
  v=hit(geom[n],t)
  if v:static.append(dict(a=n,b=other,volume_mm3=v))
# All changed parts are fixed to body, so only relative moving poses add cases.
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  for n in ids:
   for other,t in geom.items():
    if group.get(other) not in ['yaw','pitch']:continue
    v=hit(geom[n],rotate(t,yaw,pitch if group[other]=='pitch' else 0))
    if v:motion.append(dict(a=n,b=other,yaw=yaw,pitch=pitch,volume_mm3=v))
fixture={n:m for n,m in geom.items() if group.get(n)!='pitch'}
tools=[];insertion=[]
for i,x in enumerate([-26.2,26.2]):
 name='Yaw_Keeper_Screw_'+str(i)
 tf={n:(rotate(m,60) if group.get(n)=='yaw' else m) for n,m in fixture.items() if n!=name}
 p=np.array([x,0,163.55]);a=np.array([0.,0,1.])
 shapes=[axial(1.16,70,p+a*35.04,a)]
 for deg in range(0,360,5):
  t=math.radians(deg);v=np.array([math.cos(t),math.sin(t),0])
  shapes.append(axial(1.16,20,p+a*(70-1.16)+v*10,v))
 for j,m in enumerate(shapes):
  for other,t in tf.items():
   v=hit(m,t)
   if v:tools.append(dict(screw=name,piece=j,other=other,volume_mm3=v))
 for dz in np.arange(0,35.01,.5):
  for other,t in tf.items():
   v=hit(geom[name].translate((0,0,float(dz))),t)
   if v:insertion.append(dict(screw=name,lift_mm=float(dz),other=other,volume_mm3=v))
keeper=geom['Yaw_Anti_Lift_Keeper'];base=geom['Yaw_Base'];paths=[]
for dy in np.arange(0,60.01,.5):
 for n in ['Pitch_Yoke','Yaw_Servo','Pitch_Servo','Yaw_Output','Pitch_Output','Yaw_Reaction_Link','Yaw_Horn','Yaw_Lock_Screw']:
  v=hit(keeper.translate((0,float(dy),0)),geom[n])
  if v:paths.append(dict(stage='side_load',y=float(dy),other=n,volume_mm3=v))
for dz in np.arange(0,45.01,.25):
 v=hit(geom['Yaw_Bearing'].translate((0,0,float(dz))),base)
 if v:paths.append(dict(stage='bearing_lift',z=float(dz),volume_mm3=v))
yawset={n for n in geom if group.get(n)=='yaw'}|{'Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
fixed=set(geom)-yawset-{n for n in geom if group.get(n)=='pitch'}-{n for n in ids if 'Screw' in n or 'Insert' in n}-{'Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
for dz in np.arange(0,90.01,.5):
 for n in ['Pitch_Yoke','Yaw_Anti_Lift_Keeper']:
  for other in fixed:
   v=hit(geom[n].translate((0,0,float(dz))),geom[other])
   if v:paths.append(dict(stage='paired_vertical',z=float(dz),moving=n,other=other,volume_mm3=v))
capture=[]
for yaw in range(-60,61,10):
 for dz in [.39,.41,1.]:
  v=hit(rotate(geom['Pitch_Yoke'],yaw).translate((0,0,dz)),keeper)
  capture.append(dict(yaw=yaw,lift_mm=dz,overlap_mm3=v,expected='clear' if dz==.39 else 'blocked'))
mat=[]
for x in [-26.2,26.2]:
 probe=cylinder(3.625,155.4,159.39,x)-cylinder(2.025,155.39,159.4,x)
 missing=max(0,(probe-base).volume());mat.append(dict(x=x,radial_pilot_wall_probe_mm=1.6,missing_mm3=missing))
sections={}
for z in [157.,162.]:
 sections[str(z)]={tag:{n:[p.tolist() for p in source[n].slice(z).to_polygons()] for n in ['Yaw_Base','Yaw_Anti_Lift_Keeper']}
                    for tag,source in [('approved_C5',original),('candidate_K1',geom)]}
(HERE/'keeper_wall_sections.json').write_text(json.dumps(sections)+'\n')
options=json.loads((HERE/'keeper_wall_options.json').read_text())['round']
ctx.assert_unchanged()
capture_ok=all((r['overlap_mm3']==0)==(r['expected']=='clear') for r in capture)
ok=not any([static,motion,tools,insertion,paths]) and capture_ok and all(r['missing_mm3']<.01 for r in mat) and options['minimum_keeper_shell_gap']['gap_mm']>=.3
r=dict(status='PASS' if ok else 'BLOCKED',source_main_sha256=ctx.source_hash,changed=ids,static_hits=static,motion_hits=motion,head_poses=130,tool_hits=tools,screw_insertion_hits=insertion,other_paths=paths,pilot_material=mat,dimensions=dict(screw_x_mm=[-26.2,26.2],keeper_outer_d_mm=60.4,fixed_rim_inner_d_mm=61.,fixed_rim_outer_d_mm=65.4),source_geometry={n:sha(HERE/('round_'+n+'.npz')) for n in ids},head_shell_gap=options['minimum_keeper_shell_gap'],nominal_pilot_wall_mm=options['pilot_wall_min_mm'],top_counterbore_outer_edge_mm=1.,scope='Independent local candidate; original1.6mm geometric reserve restored; notPA12/insert strength qualification',main_applied=False,approval='PENDING_USER',physical_validation='NOT_TESTED',full_harness='BLOCKED',elapsed_s=time.time()-start)
r['capture']=dict(status='PASS' if capture_ok else 'FAIL',samples=capture)
r['path_samples']=dict(keeper_side=121,bearing_vertical=181,paired_vertical=181,screw_vertical_per_screw=71)
(HERE/'keeper_wall_verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('KEEPER_WALL_VERIFICATION',r['status'],[(k,len(r[k])) for k in ['static_hits','motion_hits','tool_hits','screw_insertion_hits','other_paths']],flush=True)
