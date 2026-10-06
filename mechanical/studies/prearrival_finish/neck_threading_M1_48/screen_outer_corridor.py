"""Bounded search for an unchanged-part bypass outside the yaw bearing.

Only a local, zero-pose wire corridor: neither end is connected to a PCB, and
this is not an adopted route or an assembly/whole-harness qualification.
"""
from pathlib import Path
import hashlib,json,sys,time,itertools,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path(bpy.data.filepath);before=sha(source)
assert before==json.loads((HERE/'source_audit.json').read_text())['source_main_sha256']
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
assert len(ss)==209
obstacles={n:s for n,s in ss.items() if s.hi[2]>125 and s.lo[2]<183 and s.lo[0]<44 and s.hi[0]>-44 and s.lo[1]<44 and s.hi[1]>-44}
trees={n:s.bvh() for n,s in obstacles.items()}
ez=np.array([0.,0.,1.]);R=8.;OD=.6604;gap=.3

def line(a,b):
    return np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)/.15)+1))

def curve(angle,r,zlow,ztop):
    er=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
    th=np.linspace(0,math.pi/2,101)
    lower=np.array([er*(r-R+R*math.sin(t))+ez*(zlow+R*(1-math.cos(t))) for t in th])
    upper=np.array([er*(r-R*(1-math.cos(t)))+ez*(ztop+R*math.sin(t)) for t in th])
    return np.vstack([lower,line(lower[-1],upper[0])[1:-1],upper])

def clear(points):
    chord_error=R*(1-math.cos((math.pi/2/100)/2))
    bound=OD/2+gap+np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2+chord_error+1e-4
    for n,s in obstacles.items():
        ids=np.flatnonzero(np.all(points>=s.lo-bound,axis=1)&np.all(points<=s.hi+bound,axis=1))
        for i in ids:
            dist=float(trees[n].find_nearest(Vector(points[i]))[3])
            if dist<bound:return dict(part=n,point_mm=points[i].tolist(),surface_distance_mm=dist,required_bound_mm=float(bound))
        # Surface-distance bound covers the whole curve. Test containment once
        # per contiguous potentially enclosed run, including fully internal paths.
        starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
        for i in starts:
            p=points[i]
            if np.all(p>=s.lo) and np.all(p<=s.hi):
                q=manifold.Manifold.sphere(.005,12).translate(p.tolist())
                if (q^s.m).volume()>q.volume()/2:return dict(part=n,point_mm=p.tolist(),inside=True)
    return None

rows=[];passing=[];saved={};started=time.time()
for angle in [45,135,225,315]:
    parameters=list(itertools.product([36.4,37.,37.6,38.2,39.,40.,41.],[131.,134.,137.],[162.,164.,166.,168.,170.]))
    # Motion witnesses at the upper end justify this bounded lower-exit
    # extension; do not change wire size, bend radius or model geometry.
    parameters+=list(itertools.product([37.6,38.2,39.],[137.],[159.,160.,161.]))
    for r,zlow,ztop in parameters:
        p=curve(angle,r,zlow,ztop);failure=clear(p)
        row=dict(angle_deg=angle,outer_radius_mm=r,lower_z_mm=zlow,upper_bend_start_z_mm=ztop,
                 status='FAIL' if failure else 'PASS',failure=failure)
        rows.append(row)
        if not failure:
            key='route_'+str(len(passing));row['curve_key']=key;saved[key]=p
            row['start_mm']=p[0].tolist();row['end_mm']=p[-1].tolist()
            passing.append(row.copy())
    print('OUTER_CORRIDOR',angle,'pass',len(passing),'tried',len(rows),flush=True)
report=dict(status='PASS' if passing else 'BLOCKED',scope='Local wire corridor at mechanical zero only',
    source_main_sha256=before,script_sha256=sha(__file__),revision=P['revision'],
    all_source_parts=209,tested_nearby_native_parts=sorted(obstacles),
    assumed_wire_geometry=dict(OD_mm=OD,surface_gap_mm=gap,curve_radius_mm=R),
    method='Actual native triangle surfaces; maximum sample spacing/2 plus analytic chord error bounds all centreline segments; containment is independently tested.',
    trials=rows,passing=passing,elapsed_s=time.time()-started,
    PCB_root_connections='NOT_TESTED',terminals_and_plugs='NOT_TESTED',motion_loops='NOT_TESTED',
    four_wire_packing='NOT_TESTED',whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    limitations=['Finite simple curve family; no proof of impossibility when candidates fail.',
                 'A clear local route does not establish correct bend/strain relief at actual ports.',
                 'Native purchased proxies and photo dimensions retain their documented limits.'])
np.savez_compressed(HERE/'outer_corridor_curves.npz',**saved)
assert sha(source)==before;report['main_unchanged']=True
(HERE/'outer_corridor_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('OUTER_CORRIDOR_DONE',report['status'],len(passing),flush=True)
