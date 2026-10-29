"""Replace only two explicitly inspected dangling FAULT B-layer chains.

This preparatory candidate deliberately has no replacement route yet. The
complete original chains, exact native snapshots and existing destination vias
are recorded, so removing a stub cannot be mistaken for connecting the signal.
Source board and all native rules remain unchanged.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper, Point, LineString, pcb, uid, xy

base = Path('robot/.state/c3-completion/trials')
revision = sys.argv[1]
source = base/'R140T'/'MORI_Interface_C3.kicad_pcb'
c = Copper(source)
assert c.sha == 'b3717dd38f719a3ec5be5185a2973692a9468004aa28e9e86ce1d4e110221402'
net = '/FAULT_N'
tracks = [t for t in c.segments if t.GetNetname() == net and t.GetLayer() == pcb.B_Cu]
vias = {xy(v.GetPosition()): v for v in c.vias if v.GetNetname() == net}
chains = []
selected = []
for start in [(19.15, 27.15), (21.4, 29.4)]:
    cursor = start
    chain = []
    points = [cursor]
    while cursor not in vias:
        options = [t for t in tracks if uid(t) not in [uid(x) for x in chain]
                   and cursor in [xy(t.GetStart()), xy(t.GetEnd())]]
        assert len(options) == 1, (cursor, [uid(t) for t in options])
        t = options[0]
        assert type(t).__name__ == 'PCB_TRACK'
        chain.append(t)
        a, b = xy(t.GetStart()), xy(t.GetEnd())
        cursor = b if a == cursor else a
        points.append(cursor)
        assert len(chain) < 30
        for pad in c.pads:
            land = c.shapes.get((uid(pad), 'B.Cu'))
            if pad.GetNetname() == net and land is not None:
                assert not land.intersects(LineString([a, b])), (uid(t), c.pad_name(pad))
    # Do not delete a hidden same-layer branch/tie along the chain. Exact
    # centreline intersection catches T junctions as well as shared endpoints.
    route = LineString(points)
    for t in tracks:
        if uid(t) in [uid(x) for x in chain]:
            continue
        intersection = route.intersection(LineString([xy(t.GetStart()), xy(t.GetEnd())]))
        assert intersection.is_empty or intersection.difference(Point(cursor).buffer(.000002)).is_empty, (uid(t), intersection.wkt)
    chains.append({'dangling_end_mm': start, 'existing_via_uuid': uid(vias[cursor]),
                   'existing_via_center_mm': cursor, 'track_uuids': [uid(t) for t in chain],
                   'points_mm': points, 'length_mm': sum(math.dist(a, b) for a, b in zip(points, points[1:]))})
    selected.extend(chain)
assert len(selected) == len(set(uid(t) for t in selected))
snapshots = {uid(t): {'net': t.GetNetname(), 'layer': c.board.GetLayerName(t.GetLayer()),
                     'width_mm': t.GetWidth()/1e6, 'start_mm': list(xy(t.GetStart())),
                     'end_mm': list(xy(t.GetEnd()))} for t in selected}
plan = {'revision': revision, 'board_sha256': c.sha,
        'purpose': __doc__, 'delete_copper': list(snapshots),
        'deleted_copper_expected': snapshots, 'routes': [], 'vias': []}
review = {'source_sha256': c.sha, 'scope': __doc__, 'chains': chains,
          'status': 'PREPARATORY_ONLY_NOT_CONNECTED_NOT_ACCEPTED'}
for suffix, data in [('plan', plan), ('fault-chain-review', review)]:
    p = base/(revision+'-'+suffix+'.json')
    with p.open('x') as f:
        f.write(json.dumps(data, indent=2)+'\n')
print(json.dumps(review, indent=2))
