"""Bounded one-layer UV output proposals with unchanged power/reference obstacles.
This diagnoses the short lower corridor only; no board is changed.
"""
import json,sys,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R165I-short-uv-search.json';assert not out.exists()
p=Planner(str(b/'R165I/MORI_Interface_C3.kicad_pcb'),.05,['In3.Cu'],.2);c=p.c;net='/13 {slash} Head_Fault_Delay/HEAD_UV_N'
gs=p.routing_groups(net);a=next(g for g in gs if 'U1301.1' in g['pads']);z=next(g for g in gs if 'Q1301.2' in g['pads'])
free,vf,blocked,allowed=p.geometry(net)
s=json.loads((b/'R165I-power-spine.json').read_text());assert s['source_sha256']==c.sha
sp=LineString(s['points_mm']).buffer(.24)
blocked[0]=blocked[0].union(sp.buffer(p.internal_clearance+.102))
window=box(44,28.4,64.6,34.2)
allowed[0]=allowed[0].intersection(window)
free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
r=p.solve(a,z,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),600000)
d={'scope':__doc__,'source_sha256':c.sha,'grid_mm':p.grid,'result':r,'adopted':False}
with out.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
print(json.dumps(r))
