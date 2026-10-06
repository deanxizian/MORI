"""Remove the0.19mm yaw-nut front web via a short functional insertion slot."""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import replace_owned,axial,repair_quantized_triangles
from layout_cleanup import mm_mesh
from export import topology
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
old=ss['Pitch_Yoke'].m;seat=202.0500030517578;nut=ss['Head_Yaw_Ear_0_Nut'];center=(nut.lo+nut.hi)/2
lo=np.array([-2.4,center[1],seat-4.501]);hi=np.array([2.4,-6.14,seat-2.6]);cut=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
# The old4.417AF recess was larger than the source's minimum4.32mm across
# corners. Recut to the same4.20AF trial size used by the other M2 candidates.
pc=np.array([center[0],center[1],seat-3.6])
padlo=np.array([-5.5,-17.5,seat-4.5]);padhi=np.array([5.5,-6.15,seat])
restore=axial(2.56,2.02,pc,[0,0,1],segments=6)^manifold.Manifold.cube((padhi-padlo).tolist()).translate(padlo.tolist())
pocket=axial(4.2/math.sqrt(3),2.01,pc-[0,0,.005],[0,0,1],segments=6)
through=axial(1.1,12,[center[0],center[1],seat-3],[0,0,1],segments=64)
candidate=(old+restore)-pocket-cut-through
o=bpy.data.objects[PREFIX+'Pitch_Yoke'];assert o.get('mori_owner')==OWNER
# Avoid replace_owned's whole-part0.0005mm simplification for this tiny cut.
# Quantize and repair only the actual Boolean result at Blender precision.
m=candidate.set_tolerance(.00001).simplify(.00001);d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64)
v,f,ops,bad=repair_quantized_triangles(v,f);assert not bad
m=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')));tmp=mm_mesh('yaw_nut_candidate_clean',m);mats=list(o.data.materials);o.data=tmp.data.copy();o.data.materials.clear()
for mat in mats:o.data.materials.append(mat)
o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(tmp,do_unlink=True);candidate=Solid(o).m
fixed={n:s for n,s in ss.items() if n!='Pitch_Yoke'};new_hits=[]
for n,s in fixed.items():
 v=max(0,(candidate^s.m).volume());before=max(0,(old^s.m).volume())
 if v>max(.02,before+.02):new_hits.append({'part':n,'mm3':v})
entry=[];bench=['Pitch_Yoke','Pitch_Servo','Pitch_Bearing_L','Pitch_Bearing_R']
for d in np.arange(0,12.01,.25):
 m=nut.m.translate([0,float(d),0])
 for n in bench:
  v=max(0,(m^(candidate if n=='Pitch_Yoke' else ss[n].m)).volume())
  if v>.02:entry.append({'travel_mm':float(d),'part':n,'mm3':v})
stops={}
for label,shape in [('nominal_AF4',nut.m),('conservative_min_e4_32',axial(4.32/2,1.6,center,[0,0,1],segments=6)-axial(1,1.8,center,[0,0,1]))]:
 stops[label]={}
 for sign in [-1,1]:
  for angle in range(1,31):
   tr=Matrix.Translation(Vector(center))@Matrix.Rotation(math.radians(sign*angle),4,'Z')@Matrix.Translation(-Vector(center))
   if (shape.transform(np.array(tr)[:3,:])^candidate).volume()>.02:stops[label][str(sign)]=angle;break
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  m=candidate.transform(np.array(rigidtr(yaw,0))[:3,:]);bb=np.array(m.bounding_box())
  for n,s in fixed.items():
   if s.group=='yaw':continue
   other=s.m.transform(np.array(rigidtr(yaw,pitch))[:3,:]) if s.group=='pitch' else s.m;cc=np.array(other.bounding_box())
   if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
   v=max(0,(m^other).volume())
   if v>.02:motion.append({'yaw':yaw,'pitch':pitch,'part':n,'mm3':v})
removed=max(0,(old-candidate).volume());added=max(0,(candidate-old).volume())
# Independent local bounds include a0.002mm conversion margin at the edit
# boundary. Without this, float32 cut-face rounding leaves a6e-6mm sheet
# exactly on the intended slot roof; its lateral size is not displacement.
scope_lo=np.array([-2.562,center[1]-2.562,seat-4.503]);scope_hi=np.array([2.562,-6.138,seat-2.578])
scope=manifold.Manifold.cube((scope_hi-scope_lo).tolist()).translate(scope_lo.tolist())+axial(1.102,12.004,[center[0],center[1],seat-3],[0,0,1],segments=64)
residual=((old-candidate)+(candidate-old))-scope;outside=max(0,residual.volume())
# Re-meshing the same float32 mesh can introduce micrometre boundary changes
# outside the cut. Independently bound their distance, rather than just
# accepting a small unexplained difference volume.
residual_mesh=residual.to_mesh64();before_tree=ss['Pitch_Yoke'].bvh();after_tree=Solid(o).bvh()
residual_distance=max([max(before_tree.find_nearest(Vector(p))[3],after_tree.find_nearest(Vector(p))[3]) for p in residual_mesh.vert_properties[:,:3]] or [0])
# At the existing upper pitch bore a zero-area diagonal repair moves the
# boundary1.023 micrometres. Use an explicit2 micrometre conversion budget
# and retain the measured residual, rather than claiming exact equality.
numeric_scope_ok=outside<.01 and residual_distance<.002
probes=[]
for x in [-1.8,0,1.8]:
 h=candidate.ray_cast([x,center[1],seat-2.5999],[x,center[1],seat+1])
 probes.append({'x':x,'roof_from_nut_bearing_mm':h[0].distance*(3.5999)+.0001 if h else None})
s=Solid(o);top=topology(s.v,s.f)
out={'main_updated':False,'source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'status':'PASS' if not new_hits and not entry and not motion and all(len(r)==2 for r in stops.values()) and numeric_scope_ok and not any(top[k] for k in ['degenerate_triangles','nonmanifold_edges','boundary_edges','inconsistent_edges']) else 'FAIL','slot_mm':{'x':lo[[0]].tolist()+hi[[0]].tolist(),'y':[float(lo[1]),float(hi[1])],'z':[float(lo[2]),float(hi[2])]},'pocket_AF_mm':4.2,'old_front_web_mm':.1916344745,'roof_thickness_probes':probes,'removed_mm3':removed,'added_mm3':added,'outside_declared_region_mm3':outside,'outside_residual_max_boundary_distance_mm':residual_distance,'outside_rounding_budget_mm':.002,'quantization_repairs':ops,'static_new_hits':new_hits,'poses':130,'motion_hits':motion,'nut_entry_direction':[0,1,0],'nut_entry_travel_mm':12,'nut_entry_hits':entry,'nut_rotation_contact_deg':stops,'minimum_corner_source':'sources/Bossard_DIN934.pdf: M2 e_min4.32mm; smaller regular hex is a conservative stop screen, not a full tolerance model','topology':top,'positive_components':sum(m.volume()>.001 for m in candidate.decompose()),'datums_retained':['servo','bearing','screw','nut','hole axes','pad external outline','reaction link'],'limits':'Unadopted candidate. Insert nut on detached yoke before yaw servo and reaction link; finite entry and two nut-size stop checks only. Outside-region rounding explicitly bounded below0.002mm, measured separately. Full horn interface remains deferred. Printed tolerance/retention and PA12 strength require trials.'}
(HERE/'yaw_nut_open_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));COLS['DATUMS'].hide_viewport=True;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'yaw_nut_open_candidate.blend'));print('YAW_NUT_OPEN',out,flush=True)
