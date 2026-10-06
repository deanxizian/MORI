import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled();a=Solid(bpy.data.objects[PREFIX+'Body_Lower']);tree=a.bvh()
print('Ray docs',getattr(a.m,'ray_cast',None).__doc__ if hasattr(a.m,'ray_cast') else [n for n in dir(a.m) if 'ray' in n or 'slice' in n])
for y in [50,51]:
 start=Vector((120,y,88));d=Vector((-1,0,0))
 for i in range(5):
  hit=tree.ray_cast(start,d,150)
  if hit[0] is None:break
  tri=a.f[hit[2]];print('B',y,i,list(hit[0]),list(hit[1]),a.v[tri].tolist());start=hit[0]+d*.01
 # Exact triangle barycentric intersection with line (x,y,88) in float64.
 hits=[]
 for f in a.f:
  tri=a.v[f];uv=tri[:,1:]-[y,88];A=np.vstack([uv.T,np.ones(3)])
  try:weights=np.linalg.solve(A,[0,0,1])
  except np.linalg.LinAlgError:continue
  if min(weights)>=-1e-8:hits.append(float(weights@tri[:,0]))
 print('EXACT',y,sorted(set(round(x,5) for x in hits),reverse=True)[:20])
 if hasattr(a.m,'ray_cast'):print('MANIFOLD',a.m.ray_cast([120,y,88],[-120,y,88]))
