"""Survey every existing non-GND track against its mapped ground reference.

This complements delta regression: inherited deficits remain review items.
Use the same native-pad and connected same-net plated-transfer exclusions as
audit_candidate. Geometric coverage does not establish electrical or physical
qualification, and a flagged switching node receives no automatic exception.
Input PCB files are never saved.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from copper_geometry import *


def survey(board):
    c = Copper(board)
    rows, cache = [], {}
    zone_clearance = inner_zone_clearance(c.path)
    for t in c.segments:
        net, layer = t.GetNetname(), c.board.GetLayerName(t.GetLayer())
        if net == 'GND':
            continue
        ref, key = REFERENCE[layer], (net, layer)
        if key not in cache:
            lands = unary_union([s for (u, ly), s in c.shapes.items()
                                 if ly == layer and isinstance(c.by_id[u], pcb.PAD)
                                 and c.by_id[u].GetNetname() == net])
            clearance = max([zone_clearance] + [z.GetLocalClearance()/1e6 for z in c.zones
                            if not z.GetIsRuleArea() and z.GetNetname() == 'GND'
                            and z.IsOnLayer(c.ids[ref])])
            islands = []
            for region in parts(c.copper[net, layer]):
                transfers = []
                for anchor in c.anchors(net):
                    land = c.shapes.get((uid(anchor), layer))
                    reference_land = reference_transfer_shape(c, anchor, ref)
                    if land is not None and reference_land is not None and region.intersects(land):
                        transfers.append(reference_land.buffer(clearance + .005))
                islands.append((region, unary_union(transfers)))
            cache[key] = lands, islands
        lands, islands = cache[key]
        stroke = c.shapes[uid(t), layer]
        exemptions = unary_union([ex for region, ex in islands if region.intersects(stroke)])
        missing = (stroke.difference(lands)
                   .difference(c.copper.get(('GND', ref), GeometryCollection()))
                   .difference(exemptions))
        rows.append(dict(uuid=uid(t), net=net, layer=layer, reference_layer=ref,
                         start_mm=list(xy(t.GetStart())), end_mm=list(xy(t.GetEnd())),
                         width_mm=t.GetWidth()/1e6, missing_reference_mm2=missing.area,
                         status='REVIEW_REQUIRED' if missing.area > 1e-6 else 'PASS',
                         missing_bounds_mm=list(missing.bounds) if not missing.is_empty else []))
    flags = [r for r in rows if r['status'] == 'REVIEW_REQUIRED']
    by_net = collections.defaultdict(list)
    for row in flags:
        by_net[row['net']].append(row)
    summary = [dict(net=n, tracks=len(v), sum_missing_mm2=sum(r['missing_reference_mm2'] for r in v),
                    layers=dict(collections.Counter(r['layer'] for r in v))) for n, v in by_net.items()]
    summary.sort(key=lambda r: -r['sum_missing_mm2'])
    assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
    return dict(scope=__doc__, source_sha256=c.sha, non_GND_tracks_reviewed=len(rows),
                flagged_tracks=len(flags), flagged_nets=len(summary), by_net=summary, tracks=rows,
                threshold_mm2=1e-6, source_saved=False, physical='NOT_TESTED', manufacturing_release=False,
                interpretation='Mapped-plane coverage review only, not native DRC or confirmed electrical faults. '
                               'Per-track area sums can overlap and are not measured noise or union void area.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board')
    parser.add_argument('output')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = survey(args.board)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['source_sha256', 'non_GND_tracks_reviewed',
                                          'flagged_tracks', 'flagged_nets', 'physical']}))
