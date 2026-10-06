"""Independent diagnosis of suspect near-zero-area Boolean surface queries."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
from mathutils import Vector
from float64_distance import minimum
ctx=Context()
report=json.loads((HERE/'cuts_adaptive_screen.json').read_text())
cases=report['poses'][0]['hits'];rows=[]
for stem in ['cuts','refined']:
    path=HERE/f'{stem}_Yaw_Base.npz'
    if stem=='cuts':path=HERE/'cuts_Yaw_Base_trial.npz'
    data=np.load(path);v=data['vertices_mm'];f=data['triangles']
    m=manifold.Manifold(manifold.Mesh64(v,f.astype(np.uint64)))
    tree=ctx.target(m)['tree']
    for case in cases:
        point=np.array(case['remainder_hit']['point_mm']);near=tree.find_nearest(Vector(point))
        d,index=minimum(point,v,f)
        ball=manifold.Manifold.sphere(.74,48).translate(point.tolist())
        rows.append(dict(source=str(path.relative_to(PROJECT)),pin=case['pin'],point_mm=point.tolist(),
            BVH_distance_mm=float(near[3]),BVH_triangle=int(near[2]),
            float64_all_triangle_distance_mm=d,float64_nearest_triangle=index,
            sphere_radius_mm=.74,sphere_intersection_mm3=float((ball^m).volume())))
ctx.assert_unchanged()
out=dict(status='PASS',scope='Distance algorithm diagnosis only',rows=rows,
         source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),helper_sha256=sha(HERE/'float64_distance.py'),
         main_applied=False)
(HERE/'distance_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(rows,indent=2),flush=True)
