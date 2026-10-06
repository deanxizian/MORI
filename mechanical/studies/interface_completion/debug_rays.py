import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
print('MANIFOLD_RAY', [x for x in dir(manifold.Manifold) if 'ray' in x or 'slice' in x]);print(getattr(manifold.Manifold,'ray_cast',None).__doc__)
c=json.loads((HERE/'insert_candidate.json').read_text());cases=[]
for r in c['rows']:
 s=Solid(bpy.data.objects[PREFIX+r['host']]);b=s.bvh();e=np.array(r['entry_mm']);a=np.array(r['outward']);u=np.cross(a,[1,0,0] if abs(a[0])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(a,u)
 for z in np.linspace(.25,r['length_mm']+.15,5):
  for th in np.arange(0,360,5):
   d=u*math.cos(math.radians(th))+v*math.sin(math.radians(th));q=b.ray_cast(Vector(e-a*z),Vector(d),8)
   if q[0] is None or np.dot(q[1],d)>0:
    cases.append({'id':r['id'],'stage':1,'th':int(th),'z':z,'q':[list(x) if isinstance(x,Vector) else x for x in q]});continue
   p=b.ray_cast(q[0]+Vector(d)*.002,Vector(d),300)
   if p[0] is None or np.dot(p[1],d)<0 or p[3]<1:
    cases.append({'id':r['id'],'stage':2,'th':int(th),'z':z,'q':[list(x) if isinstance(x,Vector) else x for x in q],'p':[list(x) if isinstance(x,Vector) else x for x in p]})
(HERE/'debug_rays.json').write_text(json.dumps(cases,indent=2));print('cases',len(cases),cases[:3])
