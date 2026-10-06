"""Body lead paths with circular bends and tangent straight spans.

Uses current solids, cleaned J2 and AMASS upper allocations. No hardware or
formal source is changed. Individual pools are not a completed harness.
"""
from pathlib import Path
DUBINS_SCRIPT=Path(__file__).resolve();DUBINS_DIR=DUBINS_SCRIPT.parent
DUBINS_HELPER=DUBINS_DIR/'plan_h06_documented_mates.py';__file__=str(DUBINS_HELPER)
exec(compile(DUBINS_HELPER.read_text().split('\nports=json.loads',1)[0],str(DUBINS_HELPER),'exec'),globals())
__file__=str(DUBINS_SCRIPT)
sys.path.insert(0,str(DUBINS_DIR/'body_prefix_v2'))
from curvature_paths import paths
from collections import Counter
OUT=DUBINS_DIR/'body_prefix_v2'
ports=json.loads((DUBINS_DIR/'h06_ports.json').read_text())
axes=[45,135,225,315];pools={};trials=[];start=time.time();R=7.;STAGING_RADIUS=14.8
for pin in range(1,5):
    e=np.array(ports['body']['pins'][str(pin)]);a=e+[0,0,5.]
    straight=np.linspace(e,a,101);straight_hit=clear(straight,0,{'Plug_motion_J5'})
    top=a[2]+R;drop=top-139.;alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
    entries=[];entry_fail=Counter()
    for az in range(0,360,15):
        h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
        tt=np.linspace(0,math.pi/2,121)
        entry=np.array([a+R*(1-math.cos(t))*h+[0,0,R*math.sin(t)] for t in tt])
        err=R*(1-math.cos((tt[1]-tt[0])/2));hit=clear(entry,err)
        if hit:entry_fail[hit['object']]+=1
        else:entries.append((az,h,entry,err))
    for angle in axes:
        key=f'{pin}_{angle}';pool=[];counts=Counter();fail=Counter();examples={}
        radial=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
        b=radial*STAGING_RADIUS+[0,0,139.];cend=b+radial*run+[0,0,drop]
        tt=np.linspace(0,alpha,101)
        first=np.array([cend-radial*R*math.sin(t)-[0,0,R*(1-math.cos(t))] for t in tt]);middle=first[-1]
        second=np.array([middle-radial*R*(math.sin(alpha)-math.sin(q))-[0,0,R*(math.cos(q)-math.cos(alpha))] for q in np.linspace(alpha,0,101)])
        exit_curve=np.vstack([first,second[1:]]);exit_error=R*(1-math.cos(alpha/200))
        exit_hit=clear(exit_curve,exit_error)
        assert np.linalg.norm(exit_curve[-1]-b)<1e-8
        if not straight_hit and not exit_hit:
            for az,h,entry,entry_error in entries:
                for bend in [7.,8.,9.,10.,12.,14.]:
                    for plan in paths(entry[-1,:2],h[:2],cend[:2],-radial[:2],bend):
                        counts['tried']+=1
                        if plan['analytic_length_mm']>200:counts['length_screen']+=1;continue
                        xy=plan.pop('points_xy_mm');curve=np.column_stack([xy,np.full(len(xy),top)])
                        if np.max(np.linalg.norm(xy,axis=1))>78:counts['workspace_screen']+=1;continue
                        hit=clear(curve,plan['chord_error_mm'])
                        if hit:
                            counts['clearance_rejected']+=1;fail[hit['object']]+=1
                            examples.setdefault(hit['object'],{'entry_azimuth_deg':az,'bend_radius_mm':bend,'family':plan['family'],'first_hit':hit});continue
                        full=np.vstack([straight,entry[1:],curve[1:],exit_curve[1:]])
                        counts['passed']+=1
                        pool.append({'pin':pin,'azimuth_deg':angle,'curve_mm':full.tolist(),
                            'entry_azimuth_deg':az,'planar_path':plan,'terminal_straight_allocation_mm':5.,
                            'plane_z_mm':top,'entry_bend_radius_mm':R,'exit_bend_radius_mm':R,
                            'minimum_curvature_radius_mm':min(R,bend),
                            'error_bound_mm':max(plan['chord_error_mm'],entry_error,exit_error),
                            'analytic_prefix_length_mm':5.+R*math.pi/2+plan['analytic_length_mm']+2*R*alpha})
        pools[key]=sorted(pool,key=lambda x:x['analytic_prefix_length_mm'])[:16]
        row={'pin':pin,'azimuth_deg':angle,'status':'PASS' if pool else 'BLOCKED','counts':dict(counts),
             'entry_count':len(entries),'entry_blockers':dict(entry_fail),'straight_hit':straight_hit,'exit_hit':exit_hit,
             'blockers':dict(fail),'failure_examples':examples}
        trials.append(row);print('H06_DUBINS',key,len(pool),dict(counts),dict(fail),round(time.time()-start,1),flush=True)
possible=[list(p) for p in itertools.permutations(axes) if all(pools[f'{pin}_{a}'] for pin,a in enumerate(p,1))]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'PASS' if possible else 'BLOCKED','scope':'Individual bounded body lead candidates, not simultaneous harness',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(DUBINS_SCRIPT),
    'source_helpers':{str(p.relative_to(PROJECT)):sha(p) for p in [DUBINS_HELPER,OUT/'curvature_paths.py']},
    'source_cleaned_J2_sha256':sha(DUBINS_DIR/'terminal_threading/cleaned/candidate.blend'),
    'source_ports_sha256':sha(DUBINS_DIR/'h06_ports.json'),
    'source_dimensions_sha256':sha(DUBINS_DIR/'amass_mating/received_dimensions.json'),
    'source_fixed_wires_sha256':sha(fixed_path),'trials':trials,'pools':pools,
    'possible_individual_phase_assignments':possible,'elapsed_s':time.time()-start,
    'wire_OD_mm':OD,'required_bend_mm':REQUIRED_R,'main_model_applied':False,'whole_harness':'BLOCKED',
    'four_wire_packing':'NOT_TESTED','dynamic_sources':'NOT_TESTED','physical_retention':'NOT_TESTED',
    'limitations':['Only zero head pose; source/mating/14 fixed wires included.',
      'AMASS solder/heatshrink/lead departure and female thickness tolerance remain unresolved.',
      'Finite planar CSC/CCC path families with radii7–14mm and length<=200mm; failure is not proof of impossible routing.']}
(OUT/'dubins_pools.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('H06_DUBINS_POOLS_COMPLETE',result['status'],len(possible),flush=True)
