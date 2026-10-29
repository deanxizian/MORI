"""Read-only alternatives for two identified signal barriers with ADC reserved.

This is a reroute proposal, not adoption. Full old-net routes stay in the source
file. Exact deletions and complete refill/regression would be required later.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask

base=Path('robot/.state/c3-completion/trials')
out=base/'R136-reroute-windows';out.mkdir(exist_ok=False)
p=Planner(str(base/'R136A/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
# Only reserve the exact crossing windows. The ADC path is not frozen.
reserve_windows={'/01 {slash} Core/IMU_SCL':[(43.7,5.5),(45.0,4.2)],
 '/01 {slash} Core/HEAD_OE_REQ_N':[(48.4,6.1),(49.7,4.8)]}
common=[]
common.extend(s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD))
common.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
common.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0)
common=unary_union(common)
def terminal(obj):
 return {'pads':[c.pad_name(obj)] if isinstance(obj,pcb.PAD) else [uid(obj)],'layers':{ly:c.shapes[(uid(obj),ly)] for ly in p.layers if (uid(obj),ly) in c.shapes}}
rows=[]
for net,padname,viaid in [('/01 {slash} Core/IMU_SCL','J102.17','eaf97512-7cec-43bc-a4d2-9fb9c0770092'),('/01 {slash} Core/HEAD_OE_REQ_N','J102.6','2ceba827-433b-44de-af01-ce89cb121093')]:
 # Own-net old reference copper can meet a new own-net transfer only in this
 # diagnostic proposal. Full retained-reference/return review still mandatory.
 guard=unary_union([c.shapes[(uid(t),c.board.GetLayerName(t.GetLayer()))].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if t.GetNetname() not in ['GND',net] and c.board.GetLayerName(t.GetLayer()) in REFERENCE]).buffer(.657)
 p.via_common=unary_union([common,guard])
 free,vf,blocked,allowed=p.geometry(net)
 window=LineString(reserve_windows[net])
 blocked=[unary_union([ob,window.buffer(.305)]) if ly=='In3.Cu' else ob for ob,ly in zip(blocked,p.layers)]
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 vf &= ~mask(window.buffer(.757),p.xx,p.yy)
 a=terminal(next(q for q in c.pads if c.pad_name(q)==padname));b=terminal(c.by_id[viaid])
 print(json.dumps({'net':net,'phase':'search'}),flush=True)
 result=p.solve(a,b,(free,vf,blocked,allowed),650000)
 row={'net':net,'source_sha256':c.sha,'scope':__doc__,'reserved_adc_scope':'Only one crossing window reserved, not the prior full diagnostic path; own-net transfer exception considered for search only, requires final audit.','result':result}
 rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='routes'}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
