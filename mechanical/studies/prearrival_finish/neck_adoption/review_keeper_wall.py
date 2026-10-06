"""Independent wall-repair options. Not applied to the approved main."""
from pathlib import Path
import sys,json,copy,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from neck_capacity import construct,cylinder,ring,box
from neck_reference import references
from mathutils.bvhtree import BVHTree
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
q=copy.deepcopy(P['neck_harness_capacity']);q['construction']['screw_xy_mm']=[[-26.2,0],[26.2,0]]
original={n:r['solid'] for n,r in references().items()};native={n:s.m for n,s in ss.items()}
moves={n:native[n].translate(((-.2 if n.endswith('_0') else .2),0,0)) for n in ['Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1']}
base_solids=construct(original,q)[0]
options={}
for label,rx,ry in [('holes_only',30.,30.),('round',30.2,30.2),('ellipse',30.2,30.)]:
 base=base_solids['Yaw_Base'];keeper=base_solids['Yaw_Anti_Lift_Keeper']
 if rx>30:
  # Continuous ellipse/round outline; shared planar bottom and unchanged C-mouth.
  outer=cylinder(1.,159.6,163.6).scale((rx,ry,1))
  blank=outer-cylinder(15.25,159.5,163.7)-box(*q['construction']['keeper_mouth_bounds'])
  for x,y in q['construction']['screw_xy_mm']:
   blank-=cylinder(1.7,159.5,163.7,x,y);blank-=cylinder(3.,161.9,163.7,x,y)
  keeper=blank
  clearance=cylinder(1.,159.6,163.9).scale((rx+.3,ry+.3,1))
  base-=clearance
 geom={'Yaw_Base':base,'Yaw_Anti_Lift_Keeper':keeper,**moves}
 gaps=[];newhits=[]
 for yaw in range(-60,61,10):
  for pitch in range(-20,26,5):
   for h in ['Head_Front','Head_Rear']:
    shell=native[h].transform(np.asarray(rigidtr(yaw,pitch))[:3,:])
    gaps.append(dict(yaw=yaw,pitch=pitch,shell=h,gap_mm=float(keeper.min_gap(shell,2))))
   for n,m in geom.items():
    for other,s in ss.items():
     if other in geom or other==n or (n=='Yaw_Base' and other.startswith('Yaw_Keeper_Insert')):continue
     t=s.m if s.group not in ['yaw','pitch'] else s.m.transform(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:])
     a=np.array(m.bounding_box());b=np.array(t.bounding_box())
     if np.any(a[3:]<=b[:3]) or np.any(b[3:]<=a[:3]):continue
     vol=float((m^t).volume())
     if vol>.01:newhits.append(dict(a=n,b=other,yaw=yaw,pitch=pitch,volume_mm3=vol))
 pilots=[]
 for x,y in q['construction']['screw_xy_mm']:
  walls=[]
  for z in np.linspace(153.85,159.35,12):
   for a in range(0,360,5):
    v=np.array([math.cos(math.radians(a)),math.sin(math.radians(a)),0]);p=np.array([x,y,z]);hs=base.ray_cast(p.tolist(),(p+v*100).tolist())
    walls.append((hs[1].distance-hs[0].distance)*100 if len(hs)>=2 else 0)
  pilots.append(min(walls))
 options[label]=dict(pilot_wall_min_mm=pilots,minimum_keeper_shell_gap=min(gaps,key=lambda x:x['gap_mm']),new_hits=newhits,
  top_counterbore_outside_edge_x_mm=rx-26.2-3.,source='INDEPENDENT CANDIDATE, NOT APPLIED')
 for n,m in geom.items():
  d=m.simplify(.0001).to_mesh64();np.savez_compressed(HERE/(label+'_'+n+'.npz'),vertices_mm=d.vert_properties[:,:3],triangles=d.tri_verts)
 print('KEEPER_WALL_OPTION',label,options[label],flush=True)
(HERE/'keeper_wall_options.json').write_text(json.dumps(options,ensure_ascii=False,indent=2)+'\n')
