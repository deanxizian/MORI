"""Bounded fixed-transfer supply bridge avoiding added unshielded TVS projection.

Original native rules are unchanged. This additional planning guard addresses
the specific I/J review finding; it is not a blanket opposite-face keepout.
"""
import json,sys,hashlib,time
from pathlib import Path
import numpy as np
from shapely import from_wkb
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner,mask
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-avoid-TVS-bridge.json';assert not out.exists()
p=Planner(str(b/'R185I/MORI_Interface_C3.kicad_pcb'),.025,['In2.Cu'],.5);c=p.c
p.xs=np.arange(55,61.001,.025);p.ys=np.arange(6,11.001,.025);p.xx,p.yy=np.meshgrid(p.xs,p.ys)
net='MOTION_3V3';free,vf,blocked,allowed=p.geometry(net)
rdir=b/'R182-supply-reservations';data=json.loads((rdir/'result.json').read_text())
assert data['source_sha256']=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
reserve=[]
for row in data['files']:
    if row['layer']!='In2.Cu' or row['net']==net:continue
    raw=(rdir/row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];reserve.append(from_wkb(raw))
specific=c.copper['/UPS_BAT','F.Cu'].difference(c.copper['GND','In1.Cu'])
base=blocked[0].union(specific.buffer(.252))
rows=[]
for label,ob in [('all_original_power_reservations',base.union(unary_union(reserve).buffer(.652))),('diagnostic_no_extra_plane_reservation',base)]:
    f=np.array([~mask(ob,p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
    a=dict(pads=[],layers={'In2.Cu':Point(58.9,8.6).buffer(.01)})
    z=dict(pads=[],layers={'In2.Cu':Point(57.2,8.05).buffer(.01)})
    start=time.monotonic();r=p.solve(a,z,(f,np.zeros(p.xx.shape,dtype=bool),[ob],allowed),150000)
    rows.append(dict(mode=label,result=r,seconds=time.monotonic()-start));print(json.dumps(dict(mode=label,result=r)),flush=True)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,original_power_source_sha256=data['source_sha256'],window_mm=[55,6,61,11],grid_mm=.025,rows=rows,adopted=False),indent=2)+'\n')
