from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'mechanical/scripts'))
from common import manifold,np
d=np.load(HERE/'refined_Pitch_Yoke.npz')
m=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
report=json.loads((HERE/'section_checks.json').read_text())
rows=[]
for r in report['walls']['Pitch_Yoke']['missing']:
    phi=math.radians(r['angle_deg']);e=np.array([math.cos(phi),math.sin(phi)])
    cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
    values=[]
    for poly in m.slice(r['z_mm']).to_polygons():
        a=np.asarray(poly);edge=np.roll(a,-1,axis=0)-a;den=cross(e,edge);valid=np.abs(den)>1e-12
        u=np.zeros(len(a));radius=np.zeros(len(a))
        u[valid]=cross(a[valid],e)/den[valid];radius[valid]=cross(a[valid],edge[valid])/den[valid]
        values.extend(radius[valid&(u>=-1e-9)&(u<1-1e-9)&(radius>0)].tolist())
    rows.append(dict(**r,raw_radius_values=sorted(values)))
print('RAY_API',[s for s in dir(m) if 'ray' in s],flush=True)
if hasattr(m,'ray_cast'):print('RAY_DOC',m.ray_cast.__doc__,flush=True)
(HERE/'wall_ambiguity.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2),flush=True)
