"""Regular-aperture geometric option; does not overwrite the released assembly."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
from optics_mount import camera_transform,camera_pupil,display_transform,apply_mount
from render import camera
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update();shell=bpy.data.objects[PREFIX+'Head_Front'];old=Solid(shell)
rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]])
p=np.array(camera_pupil());tr=np.c_[rot,p];hc=np.array([0,0,D['head_z']]);R=D['head_radius']
rays=[]
for h in np.linspace(-28.5,28.5,31):
 for v in np.linspace(-22,22,25):
  local=np.array([math.tan(math.radians(h)),math.tan(math.radians(v)),1]);d=rot@local;d/=np.linalg.norm(d);b=np.dot(p-hc,d);c=np.dot(p-hc,p-hc)-R*R;t=-b+math.sqrt(b*b-c);q=p+d*t;uvw=rot.T@(q-p)
  rays.append({'u':float(uvw[0]),'v':float(uvw[1]),'w':float(uvw[2])})
# A circular cone contains the complete rectangular declared field. Its visible sphere
# intersection is a smooth oval; no flat window or pupil change.
kh=math.sqrt(2)*math.tan(math.radians(28.5));kv=math.sqrt(2)*math.tan(math.radians(22));margin=.3
# Restore the sphere skin locally, keeping all camera capture features behind w=0.
patch=sphere('restore_camera_skin',(0,0,D['head_z']),R);boolean(patch,sphere('hollow_skin',(0,0,D['head_z']),R-P['shell_thickness_mm']))
region=manifold.Manifold.cylinder(35,13,13,128).transform(tr)
def mm(name,m):
 d=m.to_mesh64();q=mesh(name,d.vert_properties[:,:3].tolist(),d.tri_verts.tolist());SOLIDS[q.name]=m;return q
intersect(patch,mm('camera_local_restore_region',region))
# The old LCD opening remains a separate unchanged interface; never fill it while
# restoring the camera opening. Reuse the source primitive, in its original pose.
boolean(patch,apply_mount(cyl('preserve_LCD_aperture',(0,60,D['head_z']+P['display'].get('mask_z_from_head_mm',0)),P['display']['aperture_diameter_mm']/2,50,'Y'),display_transform()))
# Restrict this restoration to material outside the existing LCD interface.
# A conservative0.4mm local box around any restored-material/LCD overlap keeps
# the purchased display fixed; this never removes pre-existing shell material.
pi=Solid(patch).m;display=Solid(bpy.data.objects[PREFIX+'Display_PCB']).m
collision=pi^display
if collision.volume()>1e-6:
 bb=np.array(collision.bounding_box());lo=bb[:3]-.4;hi=bb[3:]+.4
 boolean(patch,box('retain_LCD_clearance',(lo+hi)/2,hi-lo))
union(shell,patch)
w0=0;w1=35;points=[[math.cos(a)*(margin+kh*w),math.sin(a)*(margin+kv*w),w] for w in [w0,w1] for a in np.linspace(0,2*math.pi,128,endpoint=False)];cut=manifold.Manifold.hull_points(points).transform(tr);boolean(shell,mm('regular_conical_aperture',cut))
new=Solid(shell);hits=[]
for ray in rays:
 d=rot@np.array([ray['u'],ray['v'],ray['w']]);d/=np.linalg.norm(d)
 hit=new.bvh().ray_cast(Vector(p),Vector(d),200)
 if hit[0] is not None:hits.append(ray)
# Lens and front capture must remain separate. Other solids checked without moving them.
collisions=[];baseline_collisions=[]
for o in parts():
 if o.get('role')!='part' or o.name==shell.name or o.get('group') in ['dock','coupon']:continue
 s=Solid(o)
 if np.any(new.hi<s.lo) or np.any(s.hi<new.lo):continue
 v=max(0,(new.m^s.m).volume())
 vb=max(0,(old.m^s.m).volume())
 if vb>.02:baseline_collisions.append({'part':s.name,'before_mm3':round(vb,4),'after_mm3':round(v,4)})
 if v>max(.02,vb+.01):collisions.append({'part':s.name,'mm3':round(v,4),'baseline_mm3':round(vb,4)})
report={'proposal_only':True,'status':'PASS' if not hits and not collisions and len(new.m.decompose())==1 else 'FAIL','description':'Replace overlapping circular/rectangular cuts with a single elliptical conical flare; the mother-sphere intersection appears as a continuous smooth oval. Lens and capture lips unchanged.','declared_hfov_deg':57,'declared_vfov_deg':44,'nominal_rays':len(rays),'blocked_rays':len(hits),'new_or_increased_solid_overlaps':collisions,'existing_baseline_intersections':baseline_collisions,'cone_radii_at_w_mm':{'u':'0.3 + %.6f*w'%kh,'v':'0.3 + %.6f*w'%kv},'removed_from_existing_integral_bezel_mm3':max(0,(cut^Solid(bpy.data.objects[PREFIX+'Integrated_Face_Region']).m).volume()),'sphere_intersection_uv_extent_mm':[[min(r[a] for r in rays),max(r[a] for r in rays)] for a in ['u','v','w']],'added_mm3':max(0,(new.m-old.m).volume()),'removed_mm3':max(0,(old.m-new.m).volume()),'connected_components':len(new.m.decompose()),'limitations':'Assumed57x44deg FOV and photo reconstruction, no lens calibration. Elliptical conical flare deliberately larger than rectangular ray footprint. User confirmation needed for aperture appearance.'}
(HERE/'camera_aperture_candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
from readiness_completion import paint_integral_rim
MATS['shell']=bpy.data.materials[PREFIX+'shell'];MATS['dark']=bpy.data.materials[PREFIX+'dark'];paint_integral_rim()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'camera_aperture_candidate.blend'))
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.render.resolution_x=950;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
visible={'Head_Front','Head_Rear','Camera_Lens','Camera_PCB','Display_PCB','Eye_L','Eye_R'}
for o in sc.objects:
 if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
camera('camera_aperture_option',(0,210,274),(0,20,247),98);sc.render.filepath=str(HERE/'camera_aperture_candidate.png');bpy.ops.render.render(write_still=True)
print('CAMERA_APERTURE_CANDIDATE_COMPLETE',report,flush=True)
