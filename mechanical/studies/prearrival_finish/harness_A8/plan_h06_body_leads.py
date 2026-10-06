"""Bounded H06 body-prefix study, using native pin order and J2 in memory.

No board or main-print changes; candidate exits are allocation datums. This
does not determine the complete harness, supplier cut lengths or strain relief.
"""
from pathlib import Path
TASK_SCRIPT = Path(__file__).resolve()
TASK_DIR = TASK_SCRIPT.parent
HELPER = TASK_DIR.parent / 'harness_A2/check_static.py'
__file__ = str(HELPER)
exec(compile(HELPER.read_text().split('MARGIN =')[0], str(HELPER), 'exec'), globals())
__file__ = str(TASK_SCRIPT)
from numpy.polynomial import polynomial as poly
from collections import Counter
from interface_completion import replace_owned

sample_t = np.linspace(0, 1, 65)
functions = (TASK_DIR.parent/'harness_A2/imu_individual_routes.py').read_text()
exec(compile('def bezier'+functions.split('def bezier',1)[1].split('def check_points',1)[0], str(TASK_SCRIPT), 'exec'), globals())
out_dir = TASK_DIR/'body_leads'; out_dir.mkdir(exist_ok=True)
j2 = json.loads((TASK_DIR/'terminal_threading/candidate_screen.json').read_text())
assert j2['status']=='PASS' and j2['source_blend_sha256']==source_hash
for name in ['Yaw_Base','Pitch_Yoke']:
    cache=np.load(TASK_DIR/'terminal_threading'/f'{name}_candidate.npz')
    m=manifold.Manifold(manifold.Mesh64(vert_properties=cache['vertices_mm'],tri_verts=cache['triangles'].astype(np.uint64)))
    obj=ss[name].o; replace_owned(name,m); ss[name]=Solid(obj)
    obstacles[name]=ss[name];trees[name]=ss[name].bvh()
fixed_path=TASK_DIR.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json'
fixed_data=json.loads(fixed_path.read_text())
fixed={}
for n,r in fixed_data.items():
    v=np.asarray(r['vertices_mm']);f=np.asarray(r['triangles'],dtype=np.uint64)
    fixed[n]={'lo':v.min(0),'hi':v.max(0),'m':manifold.Manifold(manifold.Mesh64(vert_properties=v,tri_verts=f)),
              'tree':BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)}
OD=.6604; MARGIN=.3; REQUIRED_R=6.9342

def clear(points,error,ignore=()):
    """Distance coverage plus a closed-solid containment test, not face normals."""
    allowance=OD/2+MARGIN+np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2+error+1e-4
    for name,s in obstacles.items():
        if name in ignore:continue
        mask=np.all(points>=s.lo-allowance,axis=1)&np.all(points<=s.hi+allowance,axis=1)
        for pt in points[mask]:
            d=trees[name].find_nearest(Vector(pt))[3]
            if d<allowance:return {'object':name,'point_mm':pt.tolist(),'distance_mm':d,'required_mm':allowance}
        if np.all(points>=s.lo) and np.all(points<=s.hi):
            tiny=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (tiny^s.m).volume()>tiny.volume()/2:return {'object':name,'inside':True}
    for name,r in fixed.items():
        mask=np.all(points>=r['lo']-allowance,axis=1)&np.all(points<=r['hi']+allowance,axis=1)
        for pt in points[mask]:
            d=r['tree'].find_nearest(Vector(pt))[3]
            if d<allowance:return {'object':name,'point_mm':pt.tolist(),'distance_mm':d,'required_mm':allowance}
        if np.all(points>=r['lo']) and np.all(points<=r['hi']):
            tiny=manifold.Manifold.sphere(.01,16).translate(points[0].tolist())
            if (tiny^r['m']).volume()>tiny.volume()/2:return {'object':name,'inside':True}
    return None

ports=json.loads((TASK_DIR/'h06_ports.json').read_text())
joined=json.loads((TASK_DIR/'joined_entry_screen.json').read_text())
assert ports['source_blend_sha256']==joined['source_blend_sha256']==source_hash
axes=[45,135,225,315];pools={};trials=[];start=time.time()
for pin in range(1,5):
    e=np.array(ports['body']['pins'][str(pin)])
    a=e+np.array([0,0,5.])
    terminal_points=np.linspace(e,a,101)
    straight_hit=clear(terminal_points,0,{'Plug_motion_J5'})
    for angle in axes:
        k=f'{pin}_{angle}'; pool=[];count=Counter(); blockers=Counter();failure_examples={}
        radial=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
        b=radial*32+np.array([0,0,139.])
        base=next(r for r in joined['rows'] if r['yaw_deg']==0 and r['azimuth_deg']==angle)
        assert np.linalg.norm(b-np.array(base['curve_mm'][0]))<1e-6
        if not straight_hit:
            for h0,h1 in itertools.product([14.,18.,22.,26.,30.],[12.,16.,20.,24.,28.]):
                count['tried']+=1
                c=np.array([a,a+[0,0,h0],b+radial*h1,b])
                if radius_at_samples(c)<REQUIRED_R:count['curvature_rejected']+=1;continue
                ts=np.linspace(0,1,401);curve=bezier(c,ts)
                error=6*max(np.linalg.norm(c[2]-2*c[1]+c[0]),np.linalg.norm(c[3]-2*c[2]+c[1]))/(8*400**2)
                hit=clear(curve,error)
                if hit:
                    count['clearance_rejected']+=1;blockers[hit['object']]+=1
                    failure_examples.setdefault(hit['object'],{'controls_mm':c.tolist(),'first_hit':hit})
                    continue
                r,at=extrema_radius(c)
                if r<REQUIRED_R:count['curvature_extrema_rejected']+=1;continue
                full=np.vstack([terminal_points,curve[1:]])
                count['passed']+=1
                pool.append({'pin':pin,'azimuth_deg':angle,'curve_mm':full.tolist(),'controls_mm':c.tolist(),
                    'terminal_straight_allocation_mm':5.,'error_bound_mm':error,
                    'minimum_curvature_radius_mm':r,'curvature_extrema_parameters':at,
                    'geometric_prefix_length_mm':float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum())})
        pools[k]=sorted(pool,key=lambda x:x['geometric_prefix_length_mm'])
        row={'pin':pin,'azimuth_deg':angle,'status':'PASS' if pool else 'BLOCKED',
             'straight_hit':straight_hit,'counts':dict(count),'blockers':dict(blockers),'failure_examples':failure_examples}
        trials.append(row);print('H06_PREFIX_POOL',k,len(pool),dict(count),dict(blockers),flush=True)

report={'status':'PASS' if any(all(pools[f'{pin}_{a}'] for pin,a in enumerate(perm,1)) for perm in itertools.permutations(axes)) else 'BLOCKED',
    'scope':'Bounded single-cubic individual body-prefix pools, not four-wire packing or complete harness',
    'source_blend_sha256':source_hash,'source_script_sha256':hashlib.sha256(TASK_SCRIPT.read_bytes()).hexdigest(),
    'source_J2_sha256':hashlib.sha256((TASK_DIR/'terminal_threading/candidate_screen.json').read_bytes()).hexdigest(),
    'source_ports_sha256':hashlib.sha256((TASK_DIR/'h06_ports.json').read_bytes()).hexdigest(),
    'source_fixed_wires_sha256':hashlib.sha256(fixed_path.read_bytes()).hexdigest(),
    'source_installed_routes_sha256':hashlib.sha256((TASK_DIR/'joined_entry_screen.json').read_bytes()).hexdigest(),
    'wire_OD_mm':OD,'required_radius_mm':REQUIRED_R,'source_objects':len(ss),'mated_allocations':len(plug),
    'fixed_wires':len(fixed),'pools':pools,'trials':trials,'elapsed_s':time.time()-start,
    'main_model_applied':False,'four_simultaneous_wires':'NOT_TESTED','physical_retention':'NOT_TESTED',
    'complete_harness':'BLOCKED','cut_lengths_released':False,
    'limitations':['Temporary J2 prints remain independent and unapproved.',
       'Native pad pitch and pin numbers are documented; crimp exit plane and terminal straight are allocations.',
       'Finite single-cubic family; failure does not prove all routing impossible.',
       'Only zero head pose screened here; final joint selection needs full moving sources, self/other wire checks and fixation.']}
(out_dir/'prefix_pools.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('H06_BODY_PREFIX_COMPLETE',report['status'],round(time.time()-start,2),flush=True)
