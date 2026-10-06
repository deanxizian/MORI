"""Unadopted local alternatives for the camera floor and two thin nut walls."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad,rigidtr
from interface_completion import axial,replace_owned
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
old={n:s.m for n,s in ss.items()};new=dict(old)
def boxm(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
def hexX(af,depth,center):
    rot=np.array([[0,0,1],[1,0,0],[0,1,0]])
    return manifold.Manifold.cylinder(depth,af/math.sqrt(3),af/math.sqrt(3),6,center=True).transform(np.c_[rot,center])
# This is the superseded rectangular package-clearance slot, below the
# present camera pocket. Refill inside the unchanged16x3mm optical mast only.
fill=boxm([-6.31,27.5,257.35],[6.31,30.5,259.801])
new['Display_Frame']=old['Display_Frame']+fill
# Rear yaw nut: recover the full4.5mm pad, keep its original through-hole;
# use the unchanged flat underside as nut bearing surface.
r=json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears'];rows={x['id']:x for x in r}
name='Head_Yaw_Ear_0';row=rows[name];x,y,z=row['seat_point_mm'];floor=z-P['head_servo_detail']['mount']['yaw_pad_thickness_mm']
rest=axial(2.57,4.5,[x,y,z-2.25],[0,0,1],segments=64)
new['Pitch_Yoke']=(old['Pitch_Yoke']+rest)-axial(1.1,10,[x,y,z-1],[0,0,1],segments=64)
cy=np.array([x,y,floor-.8]);new[name+'_Nut']=axial(4/math.sqrt(3),1.6,cy,[0,0,1],segments=6)-axial(1,2,cy,[0,0,1])
f=np.array(row['ear_top_mm']);new[name+'_Screw']=axial(1,8.02,f+[0,0,-3.99],[0,0,1])+axial(1.75,1.4,f+[0,0,.7],[0,0,1])
# Upper pitch nut: move only the metal nut/pocket into the existing ear
# support, away from the bearing cheek. Ear axis and servo pose remain fixed.
name='Head_Pitch_Ear_0';row=rows[name];f=np.array(row['ear_top_mm']);z=f[2]
restore=axial(2.57,3.05,[-40.625,0,z],[1,0,0],segments=64)^boxm([-42,-8,226],[-36,8,236])
new['Pitch_Yoke']+=restore
new['Pitch_Yoke']-=axial(6.25,16,[-39,0,D['head_z']],[1,0,0],segments=64)
# Close the old through-hole outboard of the shorter screw tip.
new['Pitch_Yoke']+=axial(1.105,6.6,[-38.7,0,z],[1,0,0])^boxm([-42,-8,226],[-36,8,236])
center=np.array([-33.8,0,z]);pocket=hexX(4.2,1.9,center)+boxm([-34.75,0,z-2.1],[-32.85,8,z+2.1])
new['Pitch_Yoke']-=pocket
new[name+'_Nut']=hexX(4,1.6,center)-axial(1,2,center,[1,0,0])
new[name+'_Screw']=axial(1,8.02,f+[-3.99,0,0],[1,0,0])+axial(1.75,1.4,f+[.7,0,0],[1,0,0])
changed=[n for n in new if max(0,((new[n]-old[n])+(old[n]-new[n])).volume())>.0001]
coll=[]
for n in changed:
 for k in new:
  if n==k:continue
  bb=np.array(new[n].bounding_box());cc=np.array(new[k].bounding_box())
  if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
  v=max(0,(new[n]^new[k]).volume());prev=max(0,(old[n]^old[k]).volume())
  if v>max(.02,prev+.02):coll.append({'a':n,'b':k,'mm3':v,'previous_mm3':prev})
motion=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  posed={n:m.transform(np.array(rigidtr(yaw,pitch if ss[n].group=='pitch' else 0))[:3,:]) if ss[n].group in ['yaw','pitch'] else m for n,m in new.items()}
  for n in changed:
   for k,m in posed.items():
    if ss[n].group==ss[k].group:continue
    bb=np.array(posed[n].bounding_box());cc=np.array(m.bounding_box())
    if np.any(bb[3:]<cc[:3]) or np.any(cc[3:]<bb[:3]):continue
    v=max(0,(posed[n]^m).volume())
    if v>.02:motion.append({'yaw':yaw,'pitch':pitch,'a':n,'b':k,'mm3':v})
 print('THIN_MOUNT_MOTION',yaw,flush=True)
entry=[]
for n,direction,distance in [('Head_Yaw_Ear_0_Nut',[0,0,-1],10),('Head_Pitch_Ear_0_Nut',[0,1,0],12)]:
 hits=[]
 for d in np.arange(0,distance+.01,.25):
  m=new[n].translate((np.array(direction)*d).tolist());v=max(0,(m^new['Pitch_Yoke']).volume())
  if v>.02:hits.append([float(d),v])
 entry.append({'id':n,'direction':direction,'distance_mm':distance,'hits':hits})
data={'main_updated':False,'status':'PASS' if not coll and not motion and not any(r['hits'] for r in entry) else 'FAIL','changed':changed,'static_new_collisions':coll,'poses':130,'motion_collisions':motion,'nut_insertion':entry,'limits':'Unadopted local candidates. Exact printed walls, counterhold tool and strength require further review. No vendor part dimensions changed.'}
(HERE/'thin_mount_candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
for n in changed:replace_owned(n,new[n])
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'thin_mount_candidates.blend'))
print('THIN_MOUNT_CANDIDATE',data['status'],coll,motion[:5],entry,flush=True)
