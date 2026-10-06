"""Choose a simultaneous four-signal body layout from verified finite pools.

Keeps the electrical pin identity while assigning geometric neck slots.
No route, mount or cable procurement is applied to the production model.
"""
from pathlib import Path
import sys,json,time,itertools,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import np,sha
from common import P
from mathutils.kdtree import KDTree
from mathutils import Vector
start=time.time();r=json.loads((HERE/'body_layered_screen.json').read_text());assert r['status']=='PASS'
for p,h in r['sources'].items():assert sha(PROJECT/p)==h,p
raw=np.load(HERE/'body_layered_candidates.npz');assert sha(HERE/'body_layered_candidates.npz')==r['curve_sha256']
nr=json.loads((HERE/'spaced_entry_screen.json').read_text());neck=np.load(HERE/'spaced_entry_candidates.npz');assert sha(HERE/'spaced_entry_candidates.npz')==nr['curve_file_sha256']
ods=[s['OD_mm'] for s in P['neck_harness_capacity']['wire_allocations']]
ng=nr['results'][0]['max_chord_error_mm'];wire_gap=.3
def tree(p):
    t=KDTree(len(p))
    for i,v in enumerate(p):t.insert(Vector(v),i)
    t.balance();return t
def item(p,rad,err):
    return dict(p=p,tree=tree(p),radius=rad,error=err,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),lo=p.min(0),hi=p.max(0))
def bound(a,b,gap=.3):
    pad=a['radius']+b['radius']+gap+a['step']/2+b['step']/2+a['error']+b['error']+1e-4
    ids=np.flatnonzero(np.all(a['p']>=b['lo']-pad,axis=1)&np.all(a['p']<=b['hi']+pad,axis=1))
    if not len(ids):return dict(status='PASS',lower_bound_mm=gap,method='expanded bounding-box separation')
    d,k=min((float(b['tree'].find(Vector(a['p'][k]))[2]),k) for k in ids)
    lower=d-a['radius']-b['radius']-(a['step']+b['step'])/2-a['error']-b['error']-1e-4
    return dict(status='PASS' if lower>=gap else 'BLOCKED',lower_bound_mm=lower,method='nearest samples minus both half-steps/chord bounds',point_mm=a['p'][k].tolist())
ends=[item(neck[f'case0_wire{i}_y0'],ods[i]/2,ng) for i in range(11)]
options={p:[] for p in range(1,5)};filtered=[];geom={};rows={};prechecks=[]
for pool in r['pools'].values():
    for row in pool:
        cid=row['id'];a=item(raw[cid],.6604/2,row['chord_error_mm']);geom[cid]=a;rows[cid]=row
        hits=[]
        for j,b in enumerate(ends):
            if j==row['slot']:continue
            result=bound(a,b)
            if result['status']!='PASS':hits.append(dict(other_neck_slot=j,**result));break
        prechecks.append(dict(id=cid,status='PASS' if not hits else 'BLOCKED',hits=hits))
        if hits:filtered.append(cid)
        else:options[row['pin']].append(cid)
for pin,ids in options.items():
    ids.sort(key=lambda cid:rows[cid]['length_mm'])
    print('BODY_PACK_OPTIONS',pin,len(ids),flush=True)
cache={};trials=0
def compatible(a,b):
    global trials
    key=tuple(sorted([a,b]))
    if key not in cache:
        trials+=1;cache[key]=bound(geom[a],geom[b])
    return cache[key]['status']=='PASS'
def choose(chosen):
    if len(chosen)==4:return chosen
    pin=len(chosen)+1
    for cid in options[pin]:
        if rows[cid]['slot'] in {rows[x]['slot'] for x in chosen}:continue
        if time.time()-start>240 or trials>20000:return None
        if all(compatible(cid,old) for old in chosen):
            result=choose(chosen+[cid])
            if result:return result
    return None
selected=choose([]);selected_checks=[];combined={};self_hits=[]
if selected:
    for cid in selected:
        row=rows[cid];body=geom[cid]['p'];slot=row['slot']
        # The whole signal curve includes its own neck; detect remote self approach.
        for yaw in range(-60,61,10):
            p=np.vstack([body,neck[f'case0_wire{slot}_y{yaw}'][1:]])
            combined[f'pin{row["pin"]}_y{yaw}']=p
            s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];t=tree(p)
            safe=.6604+wire_gap+np.linalg.norm(np.diff(p,axis=0),axis=1).max()+2*max(row['chord_error_mm'],ng)+1e-4
            found=None
            for i,v in enumerate(p):
                for _,j,d in t.find_range(Vector(v),safe):
                    if abs(s[j]-s[i])>5:
                        found=dict(pin=row['pin'],yaw=yaw,i=i,j=j,distance_mm=float(d),required_bound_mm=float(safe));break
                if found:break
            if found:self_hits.append(found)
    for yaw in range(-60,61,10):
        current=[]
        mapped={rows[cid]['slot']:cid for cid in selected}
        for i in range(11):
            if i in mapped:
                row=rows[mapped[i]];p=combined[f'pin{row["pin"]}_y{yaw}'];err=max(row['chord_error_mm'],ng)
            else:p=neck[f'case0_wire{i}_y{yaw}'];err=ng
            current.append(item(p,ods[i]/2,err))
        for i,j in itertools.combinations(range(11),2):
            result=bound(current[i],current[j]);selected_checks.append(dict(a=i,b=j,yaw=yaw,**result))
    np.savez_compressed(HERE/'body_layered_four_candidates.npz',**combined)
status='PASS' if selected and not self_hits and all(t['status']=='PASS' for t in selected_checks) else 'BLOCKED'
result=dict(status=status,source_blend_sha256=r['sources']['mechanical/mori_v1_2.blend'],sources=r['sources'],selected=[rows[cid] for cid in selected] if selected else [],zero_pose_option_counts={str(k):len(v) for k,v in options.items()},prechecks=prechecks,pair_checks_evaluated=trials,whole_local_pair_checks=selected_checks,self_hits=self_hits,inputs={p.name:sha(p) for p in [HERE/'body_layered_screen.json',HERE/'spaced_entry_screen.json',HERE/'spaced_local_packing.json']},script_sha256=sha(Path(__file__)),scope='Four signal body-to-neck routes plus seven local capacity samples; not full head harness',main_changed=False,full_endpoint_routing='BLOCKED',mounting='NOT_TESTED',wired_assembly='NOT_TESTED',physical_validation='NOT_TESTED',elapsed_s=time.time()-start)
if selected:result['curve_sha256']=sha(HERE/'body_layered_four_candidates.npz')
(HERE/'body_layered_four_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('BODY_LAYERED_PACK',status,selected,'pairchecks',trials,'selfhits',len(self_hits),'failedpairs',sum(t['status']!='PASS' for t in selected_checks),flush=True)
