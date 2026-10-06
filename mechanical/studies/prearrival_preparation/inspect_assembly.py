"""Read-only inspection of the saved current assembly, in a background Blender."""
import sys,json,hashlib,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import PREFIX, bounds

def plain(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    if hasattr(v,'to_dict'):return {k:plain(x) for k,x in v.to_dict().items()}
    if hasattr(v,'to_list'):return [plain(x) for x in v.to_list()]
    return str(v)

actual={r['id'] for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text())}
rows=[]; thin=[]
for o in bpy.data.objects:
    if not o.name.startswith(PREFIX) or o.type!='MESH':continue
    name=o.name.removeprefix(PREFIX)
    props={k:plain(o[k]) for k in o.keys() if len(str(o[k]))<4000}
    row={'id':name,'bounds_mm':bounds(o),'matrix_world':[list(r) for r in o.matrix_world], 'properties':props}
    rows.append(row)
    if name not in actual or o.get('category')!='PRINTABLE' or o.get('group') in ['coupon','dock']:continue
    o.data.calc_loop_triangles()
    verts=[o.matrix_world@v.co for v in o.data.vertices]
    tris=[tuple(t.vertices) for t in o.data.loop_triangles]
    bv=BVHTree.FromPolygons(verts,tris,all_triangles=True)
    areas=np.array([t.area for t in o.data.loop_triangles]); cdf=np.cumsum(areas)
    idx=np.unique(np.searchsorted(cdf,np.linspace(0,cdf[-1],8002)[1:-1]))
    samples=[]
    for i in idx:
        t=tris[i]; a,b,c=[verts[v] for v in t]; normal=(b-a).cross(c-a).normalized(); p=(a+b+c)/3
        hit,n,j,d=bv.ray_cast(p-normal*0.0005,-normal,500)
        if hit is not None and d>0.001:
            samples.append((float(d+0.0005),list(p),int(i)))
    samples.sort()
    vals=np.array([s[0] for s in samples])
    v=np.array(verts); f=np.array(tris); a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    volumes=np.einsum('ij,ij->i',a,np.cross(b,c))/6; volume=float(volumes.sum())
    item={'id':name,'volume_mm3':volume,'method':'Area-stratified inward normal rays at triangle centroids; finite screening, not an exact global minimum',
          'rays':len(idx),'hits':len(samples),'minimum_sampled_mm':float(vals.min()) if len(vals) else None,
          'percentiles_mm':np.percentile(vals,[1,5,50,95]).tolist() if len(vals) else [],'thinest_samples':samples[:25]}
    thin.append(item); print(name,'min/percentiles',item['minimum_sampled_mm'],item['percentiles_mm'],flush=True)
out={'blend':str(bpy.data.filepath),'sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'objects':rows}
(HERE/'assembly_inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(HERE/'wall_screening.json').write_text(json.dumps({'parts':thin},ensure_ascii=False,indent=2))
print('INSPECTION_COMPLETE',len(rows),len(thin),flush=True)
