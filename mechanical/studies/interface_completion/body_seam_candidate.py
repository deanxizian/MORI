"""Unadopted body seam relocation to clear the deck during shell removal."""
import sys,json,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad
from interface_completion import axial,replace_owned
from monocoque_structure import source_build
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
old={n:s.m for n,s in ss.items()};new=dict(old);b=source_build()
def boxm(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
o=b.body_outer('body_candidate_outer');outer=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True)
o=b.body_outer('body_candidate_inner',P['shell_thickness_mm']);inner=Solid(o).m;bpy.data.objects.remove(o,do_unlink=True);skin=outer-inner
# Local restoration replaces only old seam sleeves/ribs and their bores.
# It does not alter the wheel relief, fixed frame seats or electronics.
zones=manifold.Manifold()
for sx in [-1,1]:
 for sy in [-1,1]:
  x0,x1=sorted([sx*42.9,sx*90]);y0,y1=sorted([sy*47.95,sy*60.05])
  zones+=boxm([x0,y0,0],[x1,y1,107.0])
split=D['body_z'];gap=P['seam_gap_mm']/2
for n,lo,hi in [('Body_Upper',split+gap,300),('Body_Lower',0,split-gap)]:
 new[n]=(old[n]-zones)+(skin^zones^boxm([-200,-200,lo],[200,200,hi]))
coords=[(22,71),(-22,71),(22,-71),(-22,-71)];rows=[]
for i,(x,y) in enumerate(coords):
 # Preserve original bolt axes direction and seam height, relocate XY pairs.
 upper=axial(5.7,6.4,[x,y,103.5],[0,0,1])
 upper+=boxm([min(x,math.copysign(73,x)),y-4,102.5],[max(x,math.copysign(73,x)),y+4,106.5])
 new['Body_Upper']+=upper^outer
 new['Body_Upper']-=axial(4.05/2,5.22,[x,y,102.89],[0,0,1])
 lower=axial(5.7,15.4,[x,y,92],[0,0,1])
 lower+=boxm([min(x,math.copysign(73,x)),y-4,92],[max(x,math.copysign(73,x)),y+4,96])
 new['Body_Lower']+=lower^outer
 new['Body_Lower']-=axial(1.7,20,[x,y,91],[0,0,1])+axial(3.3,94,[x,y,42],[0,0,1])
 for family in ['Screw','Insert']:
  n=f'Shell_{family}_{i}';p=(ss[n].lo+ss[n].hi)/2;new[n]=old[n].translate([x-p[0],y-p[1],0])
 # Selected insert pilot-wall sample, same current catalogue requirements.
 walls=[];bad=0
 for z in np.linspace(100.6,104.6,5):
  for a in range(0,360,5):
   d=np.array([math.cos(math.radians(a)),math.sin(math.radians(a)),0]);p=np.array([x,y,z]);hs=new['Body_Upper'].ray_cast(p.tolist(),(p+d*100).tolist());clean=[]
   for h in hs:
    if not clean or abs(h.distance-clean[-1].distance)>1e-7:clean.append(h)
   if len(clean)<2:bad+=1;continue
   walls.append((clean[1].distance-clean[0].distance)*100)
 rows.append({'i':i,'xy_mm':[x,y],'pilot_wall_min_mm':min(walls) if walls else None,'broken_samples':bad})
changed=['Body_Upper','Body_Lower']+[f'Shell_{family}_{i}' for i in range(4) for family in ['Screw','Insert']];coll=[]
own={(f'Shell_Insert_{i}','Body_Upper') for i in range(4)}
for n in changed:
 for k in new:
  if n==k or (n,k) in own or (k,n) in own:continue
  bb=np.array(new[n].bounding_box());cc=np.array(new[k].bounding_box())
  if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
  v=max(0,(new[n]^new[k]).volume());prev=max(0,(old[n]^old[k]).volume())
  if v>max(.02,prev+.02):coll.append({'a':n,'b':k,'mm3':v,'before_mm3':prev})
# Detach head/bridge and shell-mounted speaker/rear PCB, leave chassis boards,
# battery and wheel-drive stack. Tool/removal access for prerequisites separate.
moving=['Body_Upper']+[n for n in new if n.startswith(('Frame_Insert','Shell_Insert'))]
removed=[n for n in new if ss[n].group in ['yaw','pitch'] or n.startswith(('Yaw_','Speaker','Rear_Interface','USB_Receptacle','Power_Switch','Frame_Screw','Shell_Screw','Tire_','Wheel_Hub','Wheel_End')) or n=='Body_Lower']
fixed=[n for n in new if n not in moving+removed];hits=[]
for dz in np.arange(0,120.01,.5):
 for n in moving:
  m=new[n].translate([0,0,float(dz)]);bb=np.array(m.bounding_box())
  for k in fixed:
   cc=np.array(new[k].bounding_box())
   if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
   v=max(0,(m^new[k]).volume())
   if v>.05:hits.append({'dz':float(dz),'a':n,'b':k,'mm3':v})
print('BODY_SEAM_PATH_DONE',len(hits),flush=True)
out={'main_updated':False,'new_xy_mm':coords,'source_main_revision':P['revision'],'source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'original_split_z_mm':[split-gap,split+gap],'static_new_collisions':coll,'insert_wall_samples':rows,'shell_lift_mm':120,'shell_path_samples':241,'shell_path_hits':hits,'removed_first':removed,'fixed_during_lift':fixed,'limits':'Unadopted candidate. Straight vertical path deliberately reported separately from tilted accessory-retained study. Screw tools, lower-shell walls and full tolerances require separate checks.'}
(HERE/'body_seam_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for n in changed:replace_owned(n,new[n])
COLS['DATUMS'].hide_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'body_seam_candidate.blend'))
print('BODY_SEAM_CANDIDATE',coll,rows,hits[:8],flush=True)
