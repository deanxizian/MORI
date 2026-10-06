"""Whole-curve radius and length bounds for fixed-yaw transition candidates."""
from pathlib import Path
import json,hashlib,math,sys,time
import numpy as np
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent
OUT=HERE/'cam_fan_in'/sys.argv[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=OUT/'pool.json';data=json.loads(source.read_text());need=data['required_radius_mm'];started=time.time()
def split(c):
    levels=[np.array(c)]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2)
    return np.array([q[0] for q in levels]),np.array([q[-1] for q in levels[::-1]])
def radius_bound(c):
    n=len(c)-1;v=n*np.diff(c,axis=0);a=n*(n-1)*np.diff(c,n=2,axis=0)
    q=np.zeros((2*n-2,3))
    for i in range(n):
        for j in range(n-1):
            q[i+j]+=math.comb(n-1,i)*math.comb(n-2,j)/math.comb(2*n-3,i+j)*np.cross(v[i],a[j])
    lo=v.min(0);hi=v.max(0);speed=float(np.linalg.norm(np.maximum(np.maximum(lo,-hi),0.)))
    cross=float(np.linalg.norm(q,axis=1).max())
    return max(0.,speed-1e-12)**3/(cross*(1+1e-9)+1e-20)
def audit(c,depth=0,tol=1e-4):
    low=float(np.linalg.norm(c[-1]-c[0]));high=float(np.linalg.norm(np.diff(c,axis=0),axis=1).sum());rad=radius_bound(c)
    if (rad>=need and high-low<=tol) or depth>=18:
        return dict(low=max(0.,low-1e-10),high=high+1e-10,rad=rad,intervals=1,unresolved=int(rad<need or high-low>tol))
    x,y=split(c);a=audit(x,depth+1,tol/2);b=audit(y,depth+1,tol/2)
    return dict(low=a['low']+b['low'],high=a['high']+b['high'],rad=min(a['rad'],b['rad']),intervals=a['intervals']+b['intervals'],unresolved=a['unresolved']+b['unresolved'])
rows=[]
for row in data['rows']:
    for index,c in enumerate(row['candidates']):
        if c['controls_mm']:
            pieces=[audit(np.array(x)) for x in c['controls_mm']]
            low=sum(p['low'] for p in pieces);high=sum(p['high'] for p in pieces)
            rad=min(p['rad'] for p in pieces);unresolved=sum(p['unresolved'] for p in pieces)
            if c.get('arc'):
                arc=c['arc'];low+=arc['radius_mm']*arc['angle_rad']-1e-9;high+=arc['radius_mm']*arc['angle_rad']+1e-9
                rad=min(rad,arc['radius_mm']-1e-9)
                assert np.allclose(c['controls_mm'][-1][-1],arc['start_mm'],atol=1e-8)
            method='De Casteljau length and Bernstein derivative cross-product bounds; exact circle where present'
        else:
            a=np.array(c['start_mm']);b=np.array(c['end_mm']);p=c['parameters'];radii=p['radii_mm']
            four=c['curve_kind'].startswith('four circular S bends')
            assert four or c['curve_kind'].startswith('three circular S bends')
            deltas=([a[0]-p['side_x_mm'],p['side_y_mm']-a[1]] if four else [math.hypot(p['side_x_mm']-a[0],p['side_y_mm']-a[1])])+[b[0]-p['side_x_mm'],b[1]-p['side_y_mm']]
            angles=[math.acos(1-d/(2*r)) for d,r in zip(deltas,radii)]
            rises=[2*r*math.sin(t) for r,t in zip(radii,angles)]
            lines=[b[2]-a[2]-sum(rises)] if four else [p['cross_z_mm']-a[2]-rises[0],b[2]-p['cross_z_mm']-sum(rises[1:])]
            assert min(lines)>=0
            length=sum(2*r*t for r,t in zip(radii,angles))+sum(lines)
            low=length-1e-8;high=length+1e-8;rad=min(radii)-1e-9;unresolved=0
            method='Exact circular S bends and positive tangent straight spans; all inter-span tangents +Z'
        error=max(abs(low-c['length_mm']),abs(high-c['length_mm']))
        rows.append(dict(pin=row['pin'],candidate=index,status='PASS' if not unresolved and rad>=need and error<.001 else 'BLOCKED',
            length_lower_mm=low,length_upper_mm=high,minimum_radius_lower_mm=rad,maximum_length_error_mm=error,
            unresolved_intervals=unresolved,method=method))
        print('FAN_MATH',row['pin'],index,rows[-1]['status'],flush=True)
result=dict(status='PASS' if rows and all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    script_sha256=sha(SCRIPT),source_pool_sha256=sha(source),rows=rows,
    scope='Whole spans of stored individual fixed-yaw transition candidates; mutual packing and anchors separate',
    required_radius_mm=need,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'math_bounds.json').write_text(json.dumps(result,indent=2)+'\n')
