"""Unadopted 1.25mm wheel-bearing retaining lips with a matched axial stack.

Shift each inner purchased bearing0.5mm as a rigid body. Outer bearing, motor,
wheel and hub datums stay fixed; adapt only the custom shaft/spacer and seats.
"""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from interface_completion import axial,replace_owned,repair_quantized_triangles
from layout_cleanup import mm_mesh
from export import topology
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
old={n:s.m for n,s in ss.items()};new=dict(old);w=P['wheel_interface'];wz=D['wheel_z'];delta=.5
inner,outer=w['bearing_centers_abs_x_mm'];width=w['bearing_width_mm'];margin=w['bearing_seat_axial_margin_mm'];half=width/2+margin
def boxm(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def xcyl(a,b,r,sign):return axial(r,b-a,[sign*(a+b)/2,0,wz],[1,0,0])
for side,sign in [('L',-1),('R',1)]:
 for host in ['Drive_Bridge','Motor_Retainer']:
  # Restore only the old inner race pocket, clipped to the existing upper /
  # lower saddle half. The radius6.5 cylinder is within the saddle's exterior.
  fill=xcyl(inner-half-.001,inner+half+.001,w['bearing_seat_nominal_diameter_mm']/2+.001,sign)
  fill-=xcyl(inner-half-.01,inner+half+.01,w['bearing_housing_throat_diameter_mm']/2,sign)
  split=wz+(1 if host=='Drive_Bridge' else -1)*w['bearing_split_gap_mm']/2
  fill^=boxm([-80,-20,split if host=='Drive_Bridge' else 0],[80,20,100 if host=='Drive_Bridge' else split])
  new[host]=(new[host]+fill)-xcyl(inner+delta-half,inner+delta+half,w['bearing_seat_nominal_diameter_mm']/2,sign)
 new['Wheel_Bearing_'+side+'_Inner']=old['Wheel_Bearing_'+side+'_Inner'].translate([sign*delta,0,0])
 shoulder=w['shoulder_end_abs_x_mm'];add=xcyl(shoulder-.02,shoulder+delta,w['shoulder_diameter_mm']/2,sign)
 for angle in w['output_hole_angles_deg']:
  y=w['output_hole_pcd_mm']/2*math.cos(math.radians(angle));z=wz+w['output_hole_pcd_mm']/2*math.sin(math.radians(angle))
  add-=axial(w['shoulder_tool_relief_diameter_mm']/2,delta+.06,[sign*(shoulder+(delta-.02)/2),y,z],[1,0,0],segments=40)
 new['Wheel_Axle_'+side]=old['Wheel_Axle_'+side]+add
 a,b=w['spacer_spans_abs_x_mm'][0];a+=delta
 new['Wheel_Spacer_'+side+'_0']=old['Wheel_Spacer_'+side+'_0']^boxm([a if sign>0 else -b,-20,0],[b if sign>0 else -a,20,100])
changed=[n for n in new if max(0,((new[n]-old[n])+(old[n]-new[n])).volume())>.00001]
# Run all subsequent checks on the final float32 Blender geometry, including
# repair of submicron Boolean slivers at the cylindrical seat boundaries.
checks=[]
for n in changed:
 replace_owned(n,new[n]);o=bpy.data.objects[PREFIX+n];m=Solid(o).m.set_tolerance(.00005).simplify(.00005);d=m.to_mesh64()
 v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64)
 v,f,ops,bad=repair_quantized_triangles(v,f)
 if bad:raise RuntimeError('Unrepaired candidate mesh: '+n)
 m=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')))
 if m.status()!=manifold.Error.NoError:raise RuntimeError('Candidate not manifold: '+n)
 temp=mm_mesh('bearing_candidate_cleanup',m);mats=list(o.data.materials);o.data=temp.data.copy();o.data.materials.clear()
 for mat in mats:o.data.materials.append(mat)
 o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(temp,do_unlink=True)
 s=Solid(o);new[n]=s.m;top=topology(s.v,s.f)
 assert not any(top[k] for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles'])
 checks.append({'id':n,'topology':top,'positive_components':sum(m.volume()>.001 for m in s.m.decompose()),'submicron_repairs':ops})
def hits(m,fixed,tol=.02):
 bb=np.array(m.bounding_box());out=[]
 for k in fixed:
  other=new[k];cc=np.array(other.bounding_box())
  if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
  v=max(0,(m^other).volume())
  if v>tol:out.append({'part':k,'mm3':v})
 return out
static=[]
for n in changed:
 for h in hits(new[n],[k for k in new if k!=n]):
  before=max(0,(old[n]^old[h['part']]).volume())
  if h['mm3']>before+.02:static.append({'changed':n,'before_mm3':before,**h})
print('BEARING_LIP_STATIC',static,flush=True)
spin=[]
for side in ['L','R']:
 moving=[n for n,s in ss.items() if s.group=='wheel_'+side]
 fixed=['Drive_Bridge','Motor_Retainer','Body_Lower','Body_Upper','Load_Frame']+[n for n in new if n.startswith('Wheel_Cap_Clamp_')]
 for angle in range(0,361,5):
  tr=Matrix.Translation((0,0,wz))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation((0,0,-wz))
  for n in moving:
   m=new[n].transform(np.array(tr)[:3,:]);spin.extend([{'side':side,'angle':angle,'moving':n,**h} for h in hits(m,fixed)])
print('BEARING_LIP_ROTATION',len(spin),flush=True)
wheel_removed={n for n in new if n.startswith(('Tire_','Wheel_Hub_','Wheel_End_','Shell_Screw','Shell_Insert')) or n in ['Wheel_Spacer_L_1','Wheel_Spacer_R_1']}
cap_screws={n for n in new if n.startswith('Wheel_Cap_Clamp_Screw')};cap=['Motor_Retainer','Motor_Retainer_Pad_-1','Motor_Retainer_Pad_1']
cases=[('cap',cap,45,wheel_removed|cap_screws|{'Body_Lower'})]
for side in ['L','R']:
 moving=['Drive_Motor_'+side,'Wheel_Axle_'+side,'Wheel_Bearing_'+side+'_Inner','Wheel_Bearing_'+side+'_Outer','Wheel_Spacer_'+side+'_0']+[n for n in new if n.startswith(('S288_Output_'+side,'Wheel_Output_Screw_'+side))]
 cases.append(('cartridge_'+side,moving,60,wheel_removed|cap_screws|set(cap)|{'Body_Lower'}))
paths=[]
for label,moving,travel,removed in cases:
 fixed=set(new)-set(moving)-removed;errors=[]
 for distance in np.arange(0,travel+.01,.5):
  for n in moving:errors.extend([{'travel_mm':float(distance),'moving':n,**h} for h in hits(new[n].translate([0,0,-float(distance)]),fixed)])
 paths.append({'label':label,'travel_mm':travel,'step_mm':.5,'moving':moving,'removed_first':sorted(removed),'hits':errors})
 print('BEARING_LIP_PATH',label,len(errors),flush=True)
axial_stack=[];wall=[]
for side,sign in [('L',-1),('R',1)]:
 bear=new['Wheel_Bearing_'+side+'_Inner'];shaft=new['Wheel_Axle_'+side]
 axial_stack.append({'side':side,'inner_bearing_span_mm':[inner+delta-width/2,inner+delta+width/2],'shaft_shoulder_end_mm':shoulder+delta,'short_spacer_span_mm':[w['spacer_spans_abs_x_mm'][0][0]+delta,w['spacer_spans_abs_x_mm'][0][1]],'bearing_pushed_into_shoulder_0_2_mm3':max(0,(bear.translate([-sign*.2,0,0])^shaft).volume())})
 for host,radial_z in [('Drive_Bridge',5.7),('Motor_Retainer',-5.7)]:
  start=[sign*34.61,0,wz+radial_z];end=[sign*36.5,0,wz+radial_z];hh=new[host].ray_cast(start,end)
  wall.append({'side':side,'part':host,'axial_lip_mm':1.89*hh[0].distance+.01 if hh else None})
force=w['screening_total_mass_kg']*9.81*w['screening_dynamic_load_factor']/2;overhang=D['wheel_x']-outer
out={'main_updated':False,'source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'status':'FAIL' if static or spin or any(r['hits'] for r in paths) else 'PASS','proposal':{'inner_bearing_rigid_shift_outward_mm':delta,'inner_bearing_center_abs_x_mm':inner+delta,'old_axial_lip_mm':inner-half-34.6,'new_axial_lip_mm':inner+delta-half-34.6,'short_spacer_length_mm':w['spacer_spans_abs_x_mm'][0][1]-w['spacer_spans_abs_x_mm'][0][0]-delta,'unchanged':['motor output axis/face','outer bearing','wheel and hub datums','all fastener axes','print exterior'],'part_delta':0},'changed':changed,'static_new_hits':static,'wheel_rotation_samples_per_side':73,'wheel_rotation_hits':spin,'service_paths':paths,'wall_rays':wall,'axial_stack':axial_stack,'topology':checks,'load_screen':{'assumed_wheel_radial_load_N':force,'inner_reaction_before_N':force*overhang/(outer-inner),'inner_reaction_after_N':force*overhang/(outer-inner-delta),'outer_reaction_before_N':force*(1+overhang/(outer-inner)),'outer_reaction_after_N':force*(1+overhang/(outer-inner-delta))},'limits':'Unadopted custom interface candidate. Purchased bearings are rigidly translated, never scaled. Nominal closed-solid finite sampling only. Catalogue tolerances, PA12 retention strength, impact, fatigue, shaft fit and coaxiality NOT_TESTED. No machining/printing release.'}
(HERE/'bearing_lip_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
COLS['DATUMS'].hide_viewport=True;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'bearing_lip_candidate.blend'));print('BEARING_LIP_CANDIDATE',out['status'],wall,flush=True)
