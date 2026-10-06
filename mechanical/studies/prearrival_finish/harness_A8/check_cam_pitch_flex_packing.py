"""Validate continuation self/other-wire clearance, including both end pieces.

Each candidate is still prescribed geometry, not a passive elastica result or
a production drawing. All thirteen yaw and ten pitch states are included for
the moving flex versus body prefix. Keep failures and all original geometry.
"""
from pathlib import Path
PACK_SCRIPT=Path(__file__).resolve();PACK_DIR=PACK_SCRIPT.parent
PACK_HELPER=PACK_DIR/'plan_cam_pitch_flex.py';__file__=str(PACK_HELPER)
exec(compile(PACK_HELPER.read_text().split('\nall_rows=[];saved={}',1)[0],str(PACK_HELPER),'exec'),globals())
__file__=str(PACK_SCRIPT)
OUT=PACK_DIR/'cam_pitch_flex/side'
pool_path=OUT/'flex_pool.json';pool=json.loads(pool_path.read_text())
assert pool['source_main_sha256']==source_hash
all_curves=np.load(OUT/'flex_candidates.npz');body_meta=json.loads((PACK_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
body_error=max(r['curve_error_bound_mm'] for r in body_meta['rows'])
head_meta=json.loads((PACK_DIR/'cam_pitch_port/departure_screen.json').read_text())
head_family=next(r for r in head_meta['selected'] if r['direction']=='left')
from mathutils.kdtree import KDTree

def fine(points,step=.02):
    p=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)[:-1] for a,b in zip(points,points[1:])]+[points[-1:]])
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    tree=KDTree(len(p))
    for i,q in enumerate(p):tree.insert(Vector(q),i)
    tree.balance()
    return p,s,tree,float(np.max(np.linalg.norm(np.diff(p,axis=0),axis=1)))
def pair(a,b,err_a,err_b):
    pa,sa,ta,da=a;pb,sb,tb,db=b
    # AABB distance is a rigorous lower bound. Excluding farther queries does
    # not change the nearest sample pair; it avoids millions of remote probes.
    lo=pb.min(0);hi=pb.max(0)
    distances=np.linalg.norm(np.maximum(np.maximum(lo-pa,pa-hi),0.),axis=1)
    first=int(np.argmin(distances));_,j,d=tb.find(Vector(pa[first]))
    best=(float(d),first,j)
    indices=np.flatnonzero(distances<=best[0]+1e-5)
    for i in indices:
        q=pa[i]
        _,j,d=tb.find(Vector(q))
        if d<best[0]:best=(float(d),i,j)
    gap=best[0]-(da+db)/2-err_a-err_b-OD-1e-4
    return {'status':'PASS' if gap>=.3 else 'BLOCKED','gap_bound_mm':gap,'sample_indices':[int(x) for x in best[1:]]}
def self_check(sample,error):
    p,s,tree,step=sample;threshold=OD+.3+step+2*error+1e-4
    for i,q in enumerate(p):
        hits=[(j,float(d)) for _,j,d in tree.find_range(Vector(q),threshold) if abs(float(s[j]-s[i]))>2.]
        if hits:
            j,d=min(hits,key=lambda x:x[1]);return {'status':'BLOCKED','indices':[i,j],'distance_mm':d,'required_bound_mm':threshold}
    return {'status':'PASS','excluded_local_arclength_mm':2.}
def own_prefix_check(sample,prefix,err_a,err_b):
    p,s,tree,step=sample;bp,bs,bt,b_step=prefix
    required=OD+.3+(step+b_step)/2+err_a+err_b+1e-4
    lo=bp.min(0);hi=bp.max(0)
    mask=np.all(p>=lo-required,axis=1)&np.all(p<=hi+required,axis=1)
    for i in np.flatnonzero(mask):
        for _,j,d in bt.find_range(Vector(p[i]),required):
            if float(bs[-1]-bs[j]+s[i])>2.:
                return {'status':'BLOCKED','indices':[int(i),int(j)],'distance_mm':float(d),'required_bound_mm':required}
    return {'status':'PASS','excluded_local_arclength_mm':2.}

body_samples={(pin,yaw):fine(body_curves[f'pin{pin}_yaw{yaw}']) for pin in range(1,5) for yaw in range(-60,61,10)}
tails={i:head_curves[f'left_slot{i}'] for i in range(4)}
extra=[]
for name,m in [('CAM_own_UART',components['UART_4P']),('CAM_conditional_housing',housing)]:
    mm=m.to_mesh64();bb=np.array(m.bounding_box())
    extra.append((name,m,bb[:3],bb[3:],BVHTree.FromPolygons(mm.vert_properties[:,:3],mm.tri_verts.tolist(),all_triangles=True)))
checked=[];cache={};t0=time.time()
for r in pool['rows']:
    pin=r['pin'];slot=r['slot_index']
    for idx,c in enumerate(r['candidates']):
        failures=[];min_other=math.inf;maximum_length_error=0.
        for pose in c['poses']:
            pitch=pose['pitch_deg'];curve=all_curves[f'pin{pin}_candidate{idx}_pitch{pitch}']
            tr=np.asarray(rigidtr(0,pitch));tail=tails[slot]@tr[:3,:3].T+tr[:3,3]
            assert np.linalg.norm(curve[0]-body_curves[f'pin{pin}_yaw0'][-1])<1e-8
            assert np.linalg.norm(curve[-1]-tail[-1])<1e-5
            # Recheck the two real/allocated mating bodies which were removed
            # only to allow the deliberately mating end in the old helper.
            inv=np.linalg.inv(tr);local=curve@inv[:3,:3].T+inv[:3,3]
            for name,m,lo,hi,tree in extra:
                hit=check_one(local,pose['chord_error_bound_mm'],lo,hi,m,tree)
                if hit:failures.append({'type':'extra_mating_body','pitch_deg':pitch,'obstacle':name,**hit})
            # Split at the yaw-fixed datum so complete candidates can be
            # transformed to every yaw without falsely moving the body prefix.
            joined=np.vstack([curve,tail[-2::-1]])
            sample=fine(joined);error=max(pose['chord_error_bound_mm'],head_family['curve_error_bounds_mm'][slot])
            cache[pin,idx,pitch]=(sample,error,joined)
            self_result=self_check(sample,error)
            if self_result['status']!='PASS':
                failures.append({'type':'continuation_self','pitch_deg':pitch,**self_result});break
            for yaw in range(-60,61,10):
                ytr=np.asarray(rigidtr(yaw,0))
                # Nearest queries use already-resampled coordinates. No need
                # to build another KD tree for a rigidly transformed query.
                q=sample[0]@ytr[:3,:3].T+ytr[:3,3]
                qsample=(q,sample[1],None,sample[3])
                self_result=own_prefix_check(qsample,body_samples[pin,yaw],error,body_error)
                if self_result['status']!='PASS':
                    failures.append({'type':'own_prefix','yaw_deg':yaw,'pitch_deg':pitch,**self_result});break
                for other_pin in range(1,5):
                    if other_pin==pin:continue
                    pr=pair(qsample,body_samples[other_pin,yaw],error,body_error)
                    min_other=min(min_other,pr['gap_bound_mm'])
                    if pr['status']!='PASS':failures.append({'type':'other_prefix','other_pin':other_pin,'yaw_deg':yaw,'pitch_deg':pitch,**pr});break
                if failures:break
            maximum_length_error=max(maximum_length_error,abs(pose['length_mm']-c['constant_length_mm']))
            if failures:break
        checked.append({'pin':pin,'candidate':idx,'status':'PASS' if not failures else 'BLOCKED','failures':failures,
            'maximum_flex_length_error_mm':maximum_length_error,'minimum_other_prefix_gap_mm':min_other if math.isfinite(min_other) else None})
        print('PITCH_PACK_INDIVIDUAL',pin,idx,checked[-1]['status'],round(time.time()-t0,1),flush=True)

pools={pin:[r['candidate'] for r in checked if r['pin']==pin and r['status']=='PASS'] for pin in range(1,5)}
pairs=[];compat={}
for pin_a,pin_b in itertools.combinations(range(1,5),2):
    for a,b in itertools.product(pools[pin_a],pools[pin_b]):
        minimum=math.inf;failure=None
        for pitch in range(-20,26,5):
            sa,ea,_=cache[pin_a,a,pitch];sb,eb,_=cache[pin_b,b,pitch]
            row=pair(sa,sb,ea,eb);minimum=min(minimum,row['gap_bound_mm'])
            if row['status']!='PASS':failure={'pitch_deg':pitch,**row};break
        key=(pin_a,a,pin_b,b);compat[key]=failure is None
        pairs.append({'pins':[pin_a,pin_b],'candidates':[a,b],'status':'PASS' if failure is None else 'BLOCKED',
            'minimum_gap_bound_mm':minimum,'failure':failure})
    print('PITCH_PACK_PAIR',pin_a,pin_b,round(time.time()-t0,1),flush=True)
assignments=[]
for choice in itertools.product(*(pools[pin] for pin in range(1,5))):
    if all(compat[(a,choice[a-1],b,choice[b-1])] for a,b in itertools.combinations(range(1,5),2)):
        assignments.append(list(choice))
result={'status':'PASS' if assignments else 'BLOCKED',
    'scope':'Whole partial-wire self, prefix and candidate-to-candidate nominal clearance; still no anchors, continuous motion or actual crimping',
    'source_script_sha256':sha(PACK_SCRIPT),'source_helper_sha256':sha(PACK_HELPER),'source_pool_sha256':sha(pool_path),
    'source_curves_sha256':sha(OUT/'flex_candidates.npz'),'source_main_sha256':source_hash,
    'source_candidate_sha256':sha(candidate/'candidate.blend'),'head_poses':130,'rows':checked,'pairs':pairs,
    'candidate_pools_after_prefix_tests':pools,'simultaneous_assignments':assignments,
    'method':'Dense chord nearest samples with both sample half steps and both analytic curve error bounds deducted. Exact AABB lower bounds prune only remote queries. Prefix self-check inherited unchanged; new continuation self-check and every prefix-to-continuation pair checked here.',
    'main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED','anchors':'NOT_TESTED',
    'continuous_motion':'NOT_TESTED','supplier_wire_cut_lengths':'BLOCKED','elapsed_s':time.time()-t0}
(OUT/'packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PITCH_PACK_DONE',result['status'],len(assignments),flush=True)
