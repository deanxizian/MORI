"""Independent preparation for a joint OV/current-sense reroute; never an adoption.

Restore the lower CLR escape outside the moved D301 body, move the owned ARMED
via with both original connections, and remove the precisely identified OV
In3 branch so its complete connection can be replanned using the existing vias.
The known front CLR reference deficiency is deliberately retained for diagnosis.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b = Path('robot/.state/c3-completion/trials')
out = b / 'R150A-plan.json'
assert not out.exists()
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha == '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
p = json.loads((b / 'R149C-plan.json').read_text())
p.update(revision='R150A', scope=__doc__)
p['vias'][0]['position_mm'] = [31.0, 5.85]
p['move_vias'][1]['position_mm'] = [32.5, 14.0]
p['routes'][0]['points_mm'] = [[30.8, 7.0375], [30.8, 6.05], [31.0, 5.85]]
p['routes'][2]['points_mm'] = [[31.86, 5.75], [31.86, 6.4], [31.5, 6.76], [30.81, 6.76], [30.3, 6.25], [26.6, 6.25]]
p['routes'][3]['points_mm'] = [[32.1, 13.15], [32.1, 14.975], [32.025, 15.05]]
p['routes'][4]['points_mm'] = [[32.5, 14.0], [32.65, 13.85], [35.2, 13.85]]
p['routes'][5]['points_mm'] = [[32.3, 13.0], [32.5, 13.2], [32.5, 14.0]]
p['routes'].append(dict(net='/CLR_N', layer='B.Cu', width_mm=.2, points_mm=[[32.1,14.0],[32.5,14.0]]))
u = 'b049d7c8-9984-50be-a63c-ab8f19b37c43'
p['move_vias'].append(dict(uuid=u, source_expected=via_snapshot(c.board,c.by_id[u]), position_mm=[32.86,16.0], reason='Clear the explicitly translated D301 body and preserve both original ARMED branches.'))
delete = ['01c0c62f-2e70-5cdb-b96b-7826f4ff753a', 'e0b746d4-193b-52fd-b359-e8159756c433']
ov = 'Net-(U1301-INB-_{slash}_OV)'
delete += [uid(t) for t in c.segments if t.GetNetname()==ov and c.board.GetLayerName(t.GetLayer())=='In3.Cu']
assert len(delete) == 12
for u in delete:
    assert u not in p['delete_copper']
    t=c.by_id[u]
    p['delete_copper'].append(u)
    p['deleted_copper_expected'][u]=dict(net=t.GetNetname(), layer=c.board.GetLayerName(t.GetLayer()), width_mm=t.GetWidth()/1e6, start_mm=list(xy(t.GetStart())), end_mm=list(xy(t.GetEnd())))
p['routes'].extend([
    dict(net='/ARMED',layer='F.Cu',width_mm=.2,points_mm=[[32.86,14.69],[32.86,16.0]]),
    dict(net='/ARMED',layer='B.Cu',width_mm=.2,points_mm=[[32.86,16.0],[31.9,16.0],[31.75,15.85]]),
])
out.write_text(json.dumps(p,indent=2)+'\n')
print(out)
