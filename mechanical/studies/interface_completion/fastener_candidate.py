"""Correct nominal nuts and contained pockets; isolated candidate only."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad,rigidtr
from layout_cleanup import mm_mesh
from monocoque_structure import obj,source_build
load_collections();assembled();source_build().materials();bpy.context.view_layer.update()
rr=json.loads((HERE/'nut_review.json').read_text())['rows'];pp={r['id']:r for r in json.loads((HERE/'nut_seat_probes.json').read_text())};ff={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())}
before={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
rows=[];changed=set()
def trans(mid,axis,angle=0):
 return Matrix.Translation(Vector(mid))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()@Matrix.Rotation(math.radians(angle),4,'Z')
def prism(radius,depth,mid,axis,n=96,angle=0):
 return manifold.Manifold.cylinder(depth,radius,radius,n,center=True).transform(np.array(trans(mid,axis,angle))[:3,:])
def replace(n,m):
 o=obj(n);temp=mm_mesh('candidate_tmp',m.simplify(.0001));o.data=temp.data.copy();o.matrix_world=Matrix.Identity(4);SOLIDS.pop(o.name,None);bpy.data.objects.remove(temp,do_unlink=True);changed.add(n)
for row in rr:
 name=row['id'];host=row['host'];a=np.array(pp[name]['axis']);p=np.array(pp[name]['center']);h=row['height_mm'];af=row['AF_mm'];m3=row['thread']=='M3'
 if name.startswith('Yaw_Reaction_'):
  rows.append({**row,'status':'BLOCKED','reason':'Horn-dependent reaction joint remains unchanged pending manufacturer data.'});continue
 # Actual printed bearing plane; the released generic nuts floated0.10/0.15mm.
 delta=float(np.median(pp[name]['bearing_distances_mm']))-h/2;p=p+a*delta
 angle=row['hex_clocking_deg'];hm=Solid(obj(host)).m;oldhm=hm
 if name.startswith(('Face_Joint','Drive_')):
  # Restore only the known old nut channel, clipped to its local solid hull.
  # No expansion of the host silhouette or any new external lug/step.
  if name.startswith('Face_Joint'):
   outer=40.5;inner=37.;sign=1 if p[0]>0 else -1;length=outer-inner;mid=np.array([sign*(inner+outer)/2,p[1],p[2]])
   old=prism(2.75,length,mid,[1,0,0],6)
   zone=manifold.Manifold.cube([length+.05,8,8],True).translate(mid.tolist())
  else:
   top=63.05;bottom=60.95;length=top-bottom;mid=np.array([p[0],p[1],(top+bottom)/2])
   old=prism(2.75,length,mid,[0,0,1],6)
   zone=manifold.Manifold.cube([8,8,length+.05],True).translate(mid.tolist())
  local=hm^zone;support=local.hull();hm=hm+(old^support)
  # Centre fixed; a4.20AF trial pocket for a documented4.00max nut.
  # Shape-clock0 equals local tracking frame; both nut and pocket use it.
  angle=0;hm=hm-prism(4.2/math.sqrt(3),length+.03,mid,a,6,angle)
  hm=hm-prism(1.2,24,p,a)
  replace(host,hm)
 nut=prism(af/math.sqrt(3),h,p,a,6,angle)-prism(1.5 if m3 else 1,h+.1,p,a)
 replace(name,nut);o=obj(name);o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='DIN934 maximum AF/thickness envelope; chamfer and thread helix omitted';o['source_url']='https://www.accu.co.uk/hexagon-nuts/'+('7888-HPN-M3-A2' if m3 else '7884-HPN-M2-A2');o['label_zh']=row['thread']+' A2六角螺母 / DIN934尺寸基准'
 f=ff[row['screw']];face=np.array(f['tool_start_mm'])-a*f['nominal_head_height_mm'];length=f['nominal_shank_length_mm']
 if name.startswith('Face_Joint'):length=10
 if name.startswith('Drive_'):length=8
 if name.startswith(('Face_Joint','Drive_')):
  bolt=prism(1,length,face-a*length/2,a)+prism(1.75,1.4,face+a*.7,a);replace(row['screw'],bolt);o=obj(row['screw']);o['label_zh']='GB/T823 M2×'+str(length);o['data_status']='VENDOR_DOCUMENTED';o['model_fidelity']='Dimensioned envelope; thread helix and drive recess omitted'
 projection=float(np.dot(p-a*h/2-(face-a*length),a));contacts={}
 for direction in [-1,1]:
  for phi in range(1,31):
   tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(direction*phi),4,Vector(a))@Matrix.Translation(-Vector(p));v=max(0,(nut.transform(np.array(tr)[:3,:])^hm).volume())
   if v>.02:contacts[str(direction)]=phi;break
 entryhits=[];entry_direction=None;entry_trials=[]
 if name.startswith(('Face_Joint','Drive_')):
  directions=[-a] if name.startswith('Face_Joint') else [np.array([0,1 if p[1]>0 else -1,0]),-a,np.array([1 if p[0]>0 else -1,0,0])]
  for direction in directions:
   hh=[]
   for distance in np.arange(0,12.01,.5):
    v=max(0,(nut.translate((direction*distance).tolist())^hm).volume())
    if v>.02:hh.append({'distance_mm':float(distance),'volume_mm3':v})
   entry_trials.append({'direction':direction.tolist(),'hits':hh})
  chosen=min(entry_trials,key=lambda t:sum(r['volume_mm3'] for r in t['hits']));entryhits=chosen['hits'];entry_direction=chosen['direction']
 rows.append({**row,'new_center_mm':p.tolist(),'actual_seat_correction_mm':delta,'screw_length_mm':length,'positive_thread_projection_mm':projection,'clocking_deg':angle,'rotation_stops_deg':contacts,'nut_to_host_mm3':max(0,(nut^hm).volume()),'nut_entry_direction':entry_direction,'nut_entry_hits':entryhits,'entry_trials':entry_trials,'pocket_AF_mm':4.2 if name.startswith(('Face_Joint','Drive_')) else None,'status':'BLOCKED' if not contacts else 'FAIL' if entryhits or projection<-.001 else 'PASS'})
bpy.context.view_layer.update();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']};coll=[]
for n in changed:
 for k,s in ss.items():
  if k==n or not broad(ss[n],s):continue
  v=max(0,(ss[n].m^s.m).volume());old=max(0,(before[n].m^before[k].m).volume()) if k in before else 0
  if v>max(old+.02,.02):coll.append({'a':n,'b':k,'new_overlap_mm3':v,'baseline_overlap_mm3':old})
out={'main_updated':False,'status':'CANDIDATE','rows':rows,'collisions':coll,'changed':sorted(changed),'limits':'Nominal geometry only; actual PA12 nut-pocket fit, torque, retention and complete assembly need verification. Standard front yaw nut requires an accessible counterhold tool, not claimed captive.'}
(HERE/'fastener_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'fastener_candidate.blend'));print('FASTENER_CANDIDATE',len(coll),[(r['id'],r['status'],r.get('nut_entry_hits')) for r in rows],flush=True)
