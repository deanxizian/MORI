"""Screen the three moved supply transfers using source copper and trial pads.

R173A was refused after native save because a proposed 5V via intersected an
In3 signal and its read-back net changed. Do not use its copper/net connectivity
as evidence. Only its exact transformed pads/body guards are read here; retained
copper, source-net identities and reference guards come from accepted R168G.
"""
import json,sys,math
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import mask
b=Path('robot/.state/c3-completion/trials');out=b/'R173-transfer-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');a=Copper(b/'R173A/MORI_Interface_C3.kicad_pcb');plan=json.loads((b/'R173A-plan.json').read_text())
excluded=set(plan['delete_copper'])|{v['uuid'] for v in plan['move_vias']+plan['remove_obsolete_vias']}
retained=[t for t in c.segments if uid(t) not in excluded]
references=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(c.copper.get(('GND',REFERENCE[c.board.GetLayerName(t.GetLayer())]),GeometryCollection())) for t in retained if t.GetNetname()!='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
common=[s.buffer(.457) for (u,ly),s in a.shapes.items() if isinstance(a.by_id[u],pcb.PAD)]
common.extend(k['shape'].buffer(.257) for k in a.keepouts if k['vias'])
common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v) not in excluded)
common.extend(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0)
common.append(unary_union(references).buffer(.657))
rows=[]
for spec in plan['move_vias']:
 net=spec['source_expected']['net'];center=spec['position_mm'];point=Point(center)
 blocked=unary_union(common+[s.buffer(.457) for (u,ly),s in c.shapes.items() if u not in excluded and not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net])
 xs=np.arange(center[0]-3,center[0]+3.001,.05);ys=np.arange(max(.8,center[1]-4),min(34.2,center[1]+4)+.001,.05);xx,yy=np.meshgrid(xs,ys)
 good=~mask(blocked,xx,yy);pos=[[round(float(x),6),round(float(y),6)] for x,y in zip(xx[good],yy[good])]
 anchor=[44.5,6.4] if 'MOTION_5V' in net else spec['source_expected']['position_mm']
 pos.sort(key=lambda p:math.dist(p,center)+.35*math.dist(p,anchor))
 rows.append(dict(uuid=spec['uuid'],net=net,proposed_position_mm=center,proposed_passes=not blocked.intersects(point),eligible_count=len(pos),positions_mm=pos[:40]))
out.write_text(json.dumps(dict(scope=__doc__,canonical_source_sha256=c.sha,trial_pad_geometry_sha256=a.sha,rows=rows,adopted=False),indent=2)+'\n')
for r in rows:print(json.dumps({**r,'positions_mm':r['positions_mm'][:10]}),flush=True)
