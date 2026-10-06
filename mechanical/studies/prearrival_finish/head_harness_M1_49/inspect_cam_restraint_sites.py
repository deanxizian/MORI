"""Read-only distances between CAM reference restraint sites and existing printed solids."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
fr=read(BASE/'cam_side_fans/fan_screen.json');nr=read(BASE/'neck_side_tail_gentle/join_screen.json')
assert fr['status']==nr['status']=='PASS'
for r in [fr,nr]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(BASE/'neck_side_tail_gentle/tails.npz')==nr['tail_sha256']
assert sha(BASE/'cam_side_fans/fan_candidates.npz')==fr['fan_curve_sha256']
tails=np.load(BASE/'neck_side_tail_gentle/tails.npz');fan=np.load(BASE/'cam_side_fans/fan_candidates.npz')
centers=[]
for row in fr['selected']:centers.append(fan[row['key']][-1])
fixed=np.mean(centers,axis=0);ports=np.mean([tails[f'pin{p}'][0] for p in range(1,5)],axis=0)
sites=[dict(name='yaw_fixed_service_start',group='yaw',point_mm=fixed.tolist()),dict(name='pitch_CAM_exit',group='pitch',point_mm=(ports+[0,0,-2.5]).tolist())]
prints={n:s for n,s in ctx.ss.items() if s.o.get('category')=='PRINTABLE'}
if not prints:prints={n:s for n,s in ctx.ss.items() if s.o.get('part_class')=='PRINTABLE'}
assert prints,[(n,dict(s.o.items())) for n,s in list(ctx.ss.items())[:1]]
for site in sites:
    p=np.asarray(site['point_mm']);near=[]
    for n,s in prints.items():
        if s.group!=site['group']:continue
        q,normal,face,d=ctx.targets[n]['tree'].find_nearest(Vector(p))
        near.append(dict(part=n,distance_mm=float(d),nearest_point_mm=list(q),normal=list(normal),bounds_mm=[s.lo.tolist(),s.hi.tolist()]))
    site['same_group_prints_by_distance']=sorted(near,key=lambda r:r['distance_mm'])
    print('RESTRAINT_SITE',site['name'],site['point_mm'],site['same_group_prints_by_distance'][:3],flush=True)
ctx.assert_unchanged()
inputs=[BASE/'cam_side_fans/fan_screen.json',BASE/'cam_side_fans/fan_candidates.npz',BASE/'neck_side_tail_gentle/join_screen.json',BASE/'neck_side_tail_gentle/tails.npz']
r=dict(status='PASS',scope='Read-only reference-site to existing-print distances. No attachment or strength verification.',sources=ctx.sources,
       inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},sites=sites,main_changed=False,attachment_design='NOT_TESTED',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'site_inventory.json').write_text(json.dumps(r,indent=2)+'\n');print('CAM_RESTRAINT_SITE_INVENTORY PASS',flush=True)
