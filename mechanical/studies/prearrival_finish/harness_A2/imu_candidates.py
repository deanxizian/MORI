# -*- coding: utf-8 -*-
"""Try eight real-diameter numbered IMU leads around the existing deck edge."""
from pathlib import Path
import json,hashlib,time,itertools
STUDY=Path(__file__).resolve().parent
FILE=Path(__file__).resolve()
__file__=str(STUDY/'check_static.py')
helper=Path(__file__).read_text().split('specs=[')[0]
exec(compile(helper,__file__,'exec'),globals())
__file__=str(FILE)
assert ECOWIRE,'This explicit alternative study requires --ecowire'
base=json.loads((STUDY/'ecowire_joint.json').read_text());assert base['status']=='PASS'
R=5.08;od=1.016;radius=od/2
existing=[]
for row in base['routes']:
    points=np.array(row['curve_mm']);existing.append((row,points[:-1],np.diff(points,axis=0)))
def wire_clear(p):
    for row,a,v in existing:
        w=p-a;tt=np.clip(np.sum(w*v,axis=1)/np.maximum(np.sum(v*v,axis=1),1e-12),0,1)
        dist=float(np.min(np.linalg.norm(w-tt[:,None]*v,axis=1)))
        if dist<radius+row['wire_OD_max_mm']/2+.5:return row['id']
    return None
da=port_pins['motion_J4'];db=port_pins['imu_J1'];search=[];found=[];start=time.time()
families=list(itertools.product([-64,-65,-66,-67,-68,-69],[141.5,143,144.5,146,147.5],[86,87,88,89]))
for yback,zup,zdown in families:
    row=dict(y_back_mm=yback,z_up_mm=zup,z_down_mm=zdown);curves=[];failed=None
    for pin in range(1,9):
        ea=da['pins'][str(pin)];eb=db['pins'][str(pin)]
        a=ea+da['axis']*5;b=eb+db['axis']*5
        cp=clean([a,[a[0],a[1],zup],[a[0],yback,zup],[b[0],yback,zdown],[b[0],b[1],zdown],b])
        points=rounded(cp,R)
        if points is None:failed=dict(pin=pin,reason='short_bend_leg');break
        full=np.array([ea,*points,eb])
        for p in resample(points,.4):
            hh=bad_at(p,radius+.5);ww=wire_clear(p)
            if hh or ww:failed=dict(pin=pin,reason='rigid' if hh else 'wire',point_mm=p.tolist(),blockers=hh or [ww]);break
        if failed:break
        curves.append(dict(id='H04_'+str(pin),harness='H04',pin=pin,from_port='motion_J4',to_port='imu_J1',
            curve_mm=full.tolist(),controls_mm=[p.tolist() for p in cp],wire_OD_max_mm=od,
            analytic_bend_radius_mm=R,terminal_straight_mm=5,
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum())))
    row.update(status='PASS' if failed is None else 'BLOCKED',failure=failed)
    search.append(row)
    if failed is None:
        found.append(dict(family=row,routes=curves));print('IMU_FAMILY_PASS',row,flush=True)
        if len(found)>=8:break
out=dict(revision=P['revision'],source_blend_sha256=source_hash,status='PASS' if found else 'BLOCKED',
    scope='Eight IMU single-wire candidate route families; joint wire spacing/solid sweep still pending',
    search=search,candidates=found,old_six_wires_unchanged=True,extra_print_holes=False,
    alternative_wire='Alpha6711 NOT_SELECTED, static5D reference only',elapsed_s=time.time()-start,
    geometry_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,cut_lengths_released=False)
(STUDY/'ecowire_imu.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('IMU_CANDIDATES',out['status'],len(search),len(found),out['elapsed_s'],flush=True)
