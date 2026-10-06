"""H06 body prefix: R7 outlet bend, planar cubic and R7 height transition."""
from pathlib import Path
ARC_SCRIPT=Path(__file__).resolve()
BASE=ARC_SCRIPT.with_name('plan_h06_body_leads.py')
__file__=str(BASE)
exec(compile(BASE.read_text().split('ports=json.loads')[0],str(BASE),'exec'),globals())
__file__=str(ARC_SCRIPT)
ports=json.loads((TASK_DIR/'h06_ports.json').read_text())
joined=json.loads((TASK_DIR/'joined_entry_screen.json').read_text())
INNER='--inner-staging' in sys.argv
STAGING_RADIUS=14.8 if INNER else 32.
axes=[45,135,225,315];pools={};trials=[];start=time.time();R=7.
for pin in range(1,5):
    e=np.array(ports['body']['pins'][str(pin)]);a=e+[0,0,5.]
    terminal_points=np.linspace(e,a,101)
    straight_hit=clear(terminal_points,0,{'Plug_motion_J5'})
    top=a[2]+R;drop=top-139.
    assert 0<drop<2*R
    alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
    entries=[];entry_fail=Counter()
    for az in range(0,360,15):
        h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
        tt=np.linspace(0,math.pi/2,121)
        entry=np.array([a+R*(1-math.cos(t))*h+[0,0,R*math.sin(t)] for t in tt])
        err=R*(tt[1]-tt[0])**2/8
        hit=clear(entry,err)
        if hit:entry_fail[hit['object']]+=1
        else:entries.append((az,h,entry,err))
    print('H06_PREFIX_ENTRIES',pin,len(entries),dict(entry_fail),flush=True)
    for angle in axes:
        k=f'{pin}_{angle}';pool=[];count=Counter();blockers=Counter();examples={}
        radial=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
        b=radial*STAGING_RADIUS+[0,0,139.];cend=b+radial*run+[0,0,drop]
        # Horizontal tangent at both ends of this descending S curve.
        tt=np.linspace(0,alpha,101)
        first=np.array([cend-radial*R*math.sin(t)-[0,0,R*(1-math.cos(t))] for t in tt])
        middle=first[-1]
        second=np.array([middle-radial*R*(math.sin(alpha)-math.sin(q))-[0,0,R*(math.cos(q)-math.cos(alpha))]
                         for q in np.linspace(alpha,0,101)])
        exit_curve=np.vstack([first,second[1:]])
        assert np.linalg.norm(exit_curve[-1]-b)<1e-8
        exit_error=R*(alpha/100)**2/8
        exit_hit=clear(exit_curve,exit_error)
        if not straight_hit and not exit_hit:
            for az,h,entry,entry_error in entries:
                for h0,h1 in itertools.product([8.,12.,16.,20.,24.],[8.,12.,16.,20.,24.]):
                    count['tried']+=1
                    c=np.array([entry[-1],entry[-1]+h*h0,cend+radial*h1,cend])
                    if radius_at_samples(c)<REQUIRED_R:count['curvature_rejected']+=1;continue
                    curve=bezier(c,np.linspace(0,1,401))
                    error=6*max(np.linalg.norm(c[2]-2*c[1]+c[0]),np.linalg.norm(c[3]-2*c[2]+c[1]))/(8*400**2)
                    hit=clear(curve,error)
                    if hit:
                        count['clearance_rejected']+=1;blockers[hit['object']]+=1
                        examples.setdefault(hit['object'],{'controls_mm':c.tolist(),'first_hit':hit})
                        continue
                    r,at=extrema_radius(c)
                    if r<REQUIRED_R:count['curvature_extrema_rejected']+=1;continue
                    full=np.vstack([terminal_points,entry[1:],curve[1:],exit_curve[1:]])
                    count['passed']+=1
                    pool.append({'pin':pin,'azimuth_deg':angle,'curve_mm':full.tolist(),'controls_mm':c.tolist(),
                        'entry_azimuth_deg':az,'entry_arc_mm':entry.tolist(),'exit_arc_mm':exit_curve.tolist(),
                        'terminal_straight_allocation_mm':5.,'error_bound_mm':max(error,entry_error,exit_error),
                        'minimum_curvature_radius_mm':min(r,R),'curvature_extrema_parameters':at,
                        'geometric_prefix_length_mm':float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum())})
        pools[k]=sorted(pool,key=lambda x:x['geometric_prefix_length_mm'])[:30]
        row={'pin':pin,'azimuth_deg':angle,'status':'PASS' if pool else 'BLOCKED','straight_hit':straight_hit,
             'exit_transition_hit':exit_hit,'entry_count':len(entries),'entry_blockers':dict(entry_fail),
             'counts':dict(count),'blockers':dict(blockers),'failure_examples':examples}
        trials.append(row);print('H06_ARC_PREFIX_POOL',k,len(pool),dict(count),dict(blockers),flush=True)
report={'status':'PASS' if any(all(pools[f'{pin}_{a}'] for pin,a in enumerate(perm,1)) for perm in itertools.permutations(axes)) else 'BLOCKED',
    'scope':'R7 outlet, planar cubic and descending R7 S; individual pools only',
    'source_blend_sha256':source_hash,'source_script_sha256':hashlib.sha256(ARC_SCRIPT.read_bytes()).hexdigest(),
    'source_helper_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
    'source_J2_sha256':hashlib.sha256((TASK_DIR/'terminal_threading/candidate_screen.json').read_bytes()).hexdigest(),
    'source_ports_sha256':hashlib.sha256((TASK_DIR/'h06_ports.json').read_bytes()).hexdigest(),
    'source_fixed_wires_sha256':hashlib.sha256(fixed_path.read_bytes()).hexdigest(),
    'source_installed_routes_sha256':hashlib.sha256((TASK_DIR/'joined_entry_screen.json').read_bytes()).hexdigest(),
    'wire_OD_mm':OD,'required_radius_mm':REQUIRED_R,'staging_radius_mm':STAGING_RADIUS,
    'source_objects':len(ss),'mated_allocations':len(plug),
    'fixed_wires':len(fixed),'pools':pools,'trials':trials,'elapsed_s':time.time()-start,
    'main_model_applied':False,'four_simultaneous_wires':'NOT_TESTED','physical_retention':'NOT_TESTED',
    'complete_harness':'BLOCKED','cut_lengths_released':False}
(out_dir/('inner_arc_prefix_pools.json' if INNER else 'arc_prefix_pools.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('H06_ARC_PREFIX_COMPLETE',report['status'],round(time.time()-start,2),flush=True)
