"""Locate small nominal clearance failures, without altering any candidate."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from validate import rigidtr
from mathutils import Vector
ctx=Context()
def stored(path):
    a=np.load(path);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
g=ctx.target(stored(OUT/'sliding_guide_v2/addition.npz'));s=ctx.targets['Pitch_Servo'];near=[]
for a,b in [(g,s),(s,g)]:
    v=np.asarray(a['m'].to_mesh64().vert_properties[:,:3]);v=v[np.all(v>=b['lo']-.5,axis=1)&np.all(v<=b['hi']+.5,axis=1)]
    for p in v:
        q,_,_,d=b['tree'].find_nearest(Vector(p))
        if d<.5:near.append(dict(a_mm=p.tolist(),b_mm=list(q),distance_mm=float(d)))
near.sort(key=lambda r:r['distance_mm'])
c=np.load(BASE/'cam_side_fans/c6_join/candidate_curves.npz');power=[]
for pitch in [15,20,25]:
    inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)));p=c['P_J18_1_y0']@inv[:3,:3].T+inv[:3,3]
    for n in ['addition','band','head']:
        t=ctx.target(stored(OUT/'connector'/(n+'.npz')))
        ids=np.flatnonzero(np.all(p>=t['lo']-2,axis=1)&np.all(p<=t['hi']+2,axis=1));best=None
        for i in ids:
            q,_,_,d=t['tree'].find_nearest(Vector(p[i]));row=dict(part=n,pitch=pitch,point_mm=p[i].tolist(),solid_point_mm=list(q),distance_mm=float(d),world_point_mm=c['P_J18_1_y0'][i].tolist())
            if best is None or d<best['distance_mm']:best=row
        if best:power.append(best)
ctx.assert_unchanged();inputs=[OUT/'sliding_guide_v2/addition.npz',*[OUT/'connector'/(n+'.npz') for n in ['addition','band','head']],BASE/'cam_side_fans/c6_join/candidate_curves.npz']
r=dict(status='PASS',scope='Closest sampled witnesses for diagnosis only',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},guide_nearest_vertices=near[:12],power_nearest_samples=power,main_changed=False,script_sha256=sha(Path(__file__)))
(OUT/'minima.json').write_text(json.dumps(r,indent=2)+'\n');print('MINIMA',near[:4],power,flush=True)
