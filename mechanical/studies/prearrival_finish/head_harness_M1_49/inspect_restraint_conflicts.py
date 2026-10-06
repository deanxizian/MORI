"""Locate current independent restraint conflicts before changing their geometry."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes/cam_restraints'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from sliding_cam_guide_geometry import build
ctx=Context();started=time.time()
def stored(path):
    a=np.load(path);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
def describe(m):
    return dict(volume_mm3=float(m.volume()),bounds_mm=list(m.bounding_box()) if not m.is_empty() else None,components=[float(x.volume()) for x in m.decompose()])
conn={n:stored(BASE/'connector'/(n+'.npz')) for n in ['addition','band','head']};rows=[]
for left,right in [('band','addition'),('head','addition')]:rows.append(dict(left=left,right=right,**describe(conn[left]^conn[right])))
for left in ['band','head']:rows.append(dict(left=left,right='Pitch_Cradle',**describe(conn[left]^ctx.ss['Pitch_Cradle'].m)))
guide=[]
for xmax in [-28.9,-29.5,-30.,-30.3]:
    m,meta=build(root_xmax=xmax);host=ctx.ss['Pitch_Yoke'].m
    guide.append(dict(root_xmax_mm=xmax,servo_overlap=describe(m^ctx.ss['Pitch_Servo'].m),root_overlap_mm3=float((m^host).volume()),combined_components=len((m+host).decompose())))
ctx.assert_unchanged();inputs=[BASE/'connector'/(n+'.npz') for n in conn]+[HERE/'sliding_cam_guide_geometry.py']
r=dict(status='PASS',scope='Completed read-only conflict location, not a design pass',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},tie_contacts=rows,guide_roots=guide,
    main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(BASE/'conflict_locations.json').write_text(json.dumps(r,indent=2)+'\n');print('RESTRAINT_CONFLICT_LOCATIONS',rows,guide,flush=True)
