"""Bound continuous curve curvature/length for the stored finite-pose candidates.

Convex-hull bounds cover the Bezier parameter between samples. This does not
cover intermediate joint angles or claim that an unrestrained real wire takes
the prescribed shape. Run with the project CAD Python, without Blender.
"""
from pathlib import Path
import json,hashlib,math,time
import numpy as np
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;OUT=HERE/'cam_pitch_flex/side'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=OUT/'flex_pool.json';d=json.loads(source.read_text());need=d['required_radius_mm'];t0=time.time()
def split(c):
    levels=[np.array(c)]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2)
    return np.array([x[0] for x in levels]),np.array([x[-1] for x in levels[::-1]])
def radius_bound(c):
    v=5*np.diff(c,axis=0);a=20*np.diff(c,n=2,axis=0)
    q=np.zeros((8,3))
    for i in range(5):
        for j in range(4):q[i+j]+=math.comb(4,i)*math.comb(3,j)/math.comb(7,i+j)*np.cross(v[i],a[j])
    lo=v.min(0);hi=v.max(0)
    vmin=float(np.linalg.norm(np.maximum(np.maximum(lo,-hi),0.)))
    qmax=float(np.max(np.linalg.norm(q,axis=1)))
    return max(0.,vmin-1e-10)**3/(qmax+1e-10)
def audit(c,level=0,tol=1e-4):
    chord=float(np.linalg.norm(c[-1]-c[0]));polygon=float(np.linalg.norm(np.diff(c,axis=0),axis=1).sum())
    rad=radius_bound(c)
    if rad>=need and polygon-chord<=tol:
        return {'low':max(0.,chord-1e-10),'high':polygon+1e-10,'rad':rad,'intervals':1,'depth':level,'unresolved':0}
    if level>=16:return {'low':max(0.,chord-1e-10),'high':polygon+1e-10,'rad':rad,'intervals':1,'depth':level,'unresolved':1}
    aa,bb=split(c);a=audit(aa,level+1,tol/2);b=audit(bb,level+1,tol/2)
    return {'low':a['low']+b['low'],'high':a['high']+b['high'],'rad':min(a['rad'],b['rad']),
            'intervals':a['intervals']+b['intervals'],'depth':max(a['depth'],b['depth']),'unresolved':a['unresolved']+b['unresolved']}
rows=[]
for row in d['rows']:
    for i,c in enumerate(row['candidates']):
        poses=[]
        for p in c['poses']:
            aa=[audit(np.array(x)) for x in p['controls_mm']]
            low=sum(a['low'] for a in aa);high=sum(a['high'] for a in aa)
            unresolved=sum(a['unresolved'] for a in aa)
            err=max(abs(c['constant_length_mm']-low),abs(high-c['constant_length_mm']))
            poses.append({'pitch_deg':p['pitch_deg'],'length_lower_mm':low,'length_upper_mm':high,
                          'maximum_constant_length_error_bound_mm':err,'minimum_radius_bound_mm':min(a['rad'] for a in aa),
                          'intervals':sum(a['intervals'] for a in aa),'maximum_depth':max(a['depth'] for a in aa),
                          'unresolved_intervals':unresolved,'status':'PASS' if not unresolved and err<.001 else 'BLOCKED'})
        rows.append({'pin':row['pin'],'candidate':i,'status':'PASS' if all(p['status']=='PASS' for p in poses) else 'BLOCKED','poses':poses})
        print('PITCH_MATH',row['pin'],i,rows[-1]['status'],round(time.time()-t0,2),flush=True)
result={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED','source_pool_sha256':sha(source),
    'source_script_sha256':sha(SCRIPT),'scope':'Entire Bezier spans at ten finite pitch angles; prescribed geometry only',
    'method':'De Casteljau subdivision; chord/control-polygon arclength bounds; derivative convex box minimum speed and cross-product Bernstein convex hull maximum',
    'required_radius_mm':need,'maximum_length_error_allowed_mm':.001,'rows':rows,
    'continuous_joint_motion':'NOT_TESTED','passive_wire_dynamics':'NOT_TESTED','whole_harness':'BLOCKED',
    'main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-t0}
(OUT/'math_bounds.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PITCH_MATH_DONE',result['status'],flush=True)
