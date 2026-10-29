"""Extract incremental proposals from a filled, isolated SES-import board.

Never adopt a whole SES-imported board: the round trip can change old via
padstack behaviour and split source power copper. Only originally open nets
whose native filled pad-group count improved are eligible. New proposals are
re-applied to the unchanged native source and must be verified independently.
"""
import argparse
import json
from pathlib import Path

from copper_geometry import *


def harvest(source, imported, output, prefix):
    a, b = Copper(source), Copper(imported)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    ga, gb = a.pad_groups(), b.pad_groups()
    eligible = sorted(n for n, groups in ga.items()
                      if len(groups) > 1 and len(gb.get(n, [])) < len(groups)
                      and not n.startswith('unconnected-'))
    source_refs = {f.GetReference() for f in a.footprints}
    assert source_refs == {f.GetReference() for f in b.footprints}
    source_pads = {uid(p): p for p in a.pads}
    for p in b.pads:
        q = source_pads.get(uid(p))
        assert q is not None and p.GetNetname() == q.GetNetname()
        assert Point(xy(p.GetPosition())).distance(Point(xy(q.GetPosition()))) < .0002
    old_vias = {(v.GetNetname(), xy(v.GetPosition())) for v in a.vias}
    rows = []
    for i, net in enumerate(eligible, 1):
        routes, vias = [], []
        for t in b.segments:
            if t.GetNetname() != net:
                continue
            layer = b.board.GetLayerName(t.GetLayer())
            stroke = b.shapes[uid(t), layer]
            added = stroke.difference(a.copper.get((net, layer), GeometryCollection()).buffer(.003))
            if added.area > 1e-6:
                routes.append({'net': net, 'layer': layer, 'width_mm': t.GetWidth() / 1e6,
                               'points_mm': [xy(t.GetStart()), xy(t.GetEnd())],
                               'source_import_uuid': uid(t), 'new_exposed_area_mm2': added.area})
        for v in b.vias:
            if v.GetNetname() != net or (net, xy(v.GetPosition())) in old_vias:
                continue
            vias.append({'net': net, 'position_mm': xy(v.GetPosition()),
                         'diameter_mm': v.GetWidth(b.ids['F.Cu']) / 1e6,
                         'drill_mm': v.GetDrill() / 1e6})
        plan = {'revision': prefix + str(i), 'scope': 'Incremental unadopted routing proposal; native and visual review required',
                'source_board_sha256': a.sha, 'imported_board_sha256': b.sha,
                'net': net, 'source_pad_groups': ga[net], 'imported_pad_groups': gb[net],
                'routes': routes, 'vias': vias}
        (output / ('plan-' + str(i) + '.json')).write_text(json.dumps(plan, indent=2) + '\n')
        rows.append({'net': net, 'plan': 'plan-' + str(i) + '.json',
                     'group_count_before': len(ga[net]), 'group_count_imported': len(gb[net]),
                     'segments': len(routes), 'vias': len(vias)})
    report = {'source_sha256': a.sha, 'imported_sha256': b.sha, 'proposals': rows,
              'limits': ['A 3 um shape tolerance excludes round-trip polygon noise; native verification still decides connectivity.',
                         'Existing source copper, vias, footprints, zones and rules must be preserved when applying each plan.',
                         'No geometry, current, return-path, body-projection or physical qualification is inferred from eligibility.']}
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('imported')
    p.add_argument('output'); p.add_argument('prefix'); a = p.parse_args()
    harvest(a.source, a.imported, a.output, a.prefix)
