#!/usr/bin/env python3
"""Read-only native PCB inspection; does not refill, save, or route any board."""
import hashlib
import heapq
import json
import math
from pathlib import Path
import pcbnew as k

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def xy(point):
    return [round(k.ToMM(point.x), 6), round(k.ToMM(point.y), 6)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pad(fp, number):
    return next(p for p in fp.Pads() if p.GetNumber() == str(number))


def endpoint(point, layer):
    return tuple(xy(point)) + (int(layer),)


def route(board, source, destination):
    """Exact track-endpoint graph, planar lengths only; no pour or pad-area model."""
    assert source.GetNetname() == destination.GetNetname()
    graph = {}

    def edge(a, b, length, item):
        graph.setdefault(a, []).append((b, length, item))
        graph.setdefault(b, []).append((a, length, item))

    for t in board.GetTracks():
        if t.GetNetname() != source.GetNetname():
            continue
        if isinstance(t, k.PCB_VIA):
            nodes = [endpoint(t.GetPosition(), layer) for layer in
                     (k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu) if t.IsOnLayer(layer)]
            for a, b in zip(nodes, nodes[1:]):
                edge(a, b, 0, t)
        else:
            edge(endpoint(t.GetStart(), t.GetLayer()),
                 endpoint(t.GetEnd(), t.GetLayer()), k.ToMM(t.GetLength()), t)
    start = endpoint(source.GetPosition(), source.GetLayer())
    end = endpoint(destination.GetPosition(), destination.GetLayer())
    queue = [(0, start)]
    distances = {start: 0}
    previous = {}
    while queue:
        dist, u = heapq.heappop(queue)
        if dist != distances[u]:
            continue
        if u == end:
            break
        for v, length, item in graph.get(u, []):
            candidate = dist + length
            if candidate < distances.get(v, math.inf):
                distances[v] = candidate
                previous[v] = (u, item)
                heapq.heappush(queue, (candidate, v))
    if end not in distances:
        return {'status': 'NOT_APPLICABLE', 'reason': 'Exact endpoint graph lacks a path; not an electrical open diagnosis'}
    u = end
    steps = []
    while u != start:
        v, item = previous[u]
        steps.append({'start': v, 'end': u, 'uuid': item.m_Uuid.AsString(),
                      'kind': 'via' if isinstance(item, k.PCB_VIA) else 'track'})
        u = v
    steps.reverse()
    return {'status': 'PASS', 'planar_length_mm': distances[end], 'steps': steps,
            'via_count': len({s['uuid'] for s in steps if s['kind'] == 'via'})}


def board_inventory(kind, revision):
    name = 'MORI_' + kind + '_' + revision
    path = ROOT / 'hardware/v1_2/kicad' / name / (name + '.kicad_pcb')
    before = sha(path)
    board = k.LoadBoard(str(path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    result = {'file': str(path.relative_to(ROOT)), 'sha256': before, 'parts': {}, 'silkscreen': []}
    selected = {'J6', 'J15', 'TP70', 'TP71', 'R61', 'R71', 'U60', 'U70', 'C62', 'C72', 'L60', 'L70'}
    for ref, f in fps.items():
        if ref.startswith('D') or (kind == 'power' and ref in selected):
            result['parts'][ref] = {
                'value': f.GetValue(), 'footprint': str(f.GetFPID().GetLibItemName()),
                'layer': board.GetLayerName(f.GetLayer()), 'dnp': f.IsDNP(),
                'pads': [{'pin': p.GetNumber(), 'net': p.GetNetname(), 'xy_mm': xy(p.GetPosition()),
                          'size_mm': xy(p.GetSize())} for p in f.Pads()]}
    texts = list(board.GetDrawings())
    for f in fps.values():
        texts.extend(f.GraphicalItems())
        texts.extend((f.Reference(), f.Value()))
    for t in texts:
        if hasattr(t, 'GetText') and t.GetLayer() in (k.F_SilkS, k.B_SilkS) and t.IsVisible():
            result['silkscreen'].append({'text': t.GetText(), 'xy_mm': xy(t.GetPosition()),
                                        'layer': board.GetLayerName(t.GetLayer())})
    if kind == 'power':
        result['routes'] = {}
        for n in (60, 70):
            u, c, l = fps['U' + str(n)], fps['C' + str(n + 2)], fps['L' + str(n)]
            for suffix, a, b in [('SW_to_CBOOT', pad(u, 2), pad(c, 2)),
                                 ('BOOT_to_CBOOT', pad(u, 6), pad(c, 1)),
                                 ('SW_to_L', pad(u, 2), pad(l, 1)),
                                 ('quiet_GND', pad(fps['R' + str(n + 1)], 2), pad(u, 1))]:
                result['routes'][str(n) + '_' + suffix] = route(board, a, b)
        sw_nets = {pad(fps['U60'], 2).GetNetname(), pad(fps['U70'], 2).GetNetname()}
        result['SW_vias'] = [{'net': t.GetNetname(), 'xy_mm': xy(t.GetPosition()),
                              'diameter_mm': k.ToMM(t.GetWidth(k.F_Cu)), 'drill_mm': k.ToMM(t.GetDrill())}
                             for t in board.GetTracks() if isinstance(t, k.PCB_VIA) and t.GetNetname() in sw_nets]
        result['inner_tracks'] = [{'net': t.GetNetname(), 'layer': board.GetLayerName(t.GetLayer()),
                                  'uuid': t.m_Uuid.AsString(), 'start': xy(t.GetStart()), 'end': xy(t.GetEnd())}
                                 for t in board.GetTracks() if not isinstance(t, k.PCB_VIA)
                                 and t.GetLayer() in (k.In1_Cu, k.In2_Cu)]
    result['source_unchanged'] = before == sha(path)
    return result


def existing_checks(kind, revision):
    base = ROOT / ('hardware/v1_2/layout_' + revision) / 'reports' / kind
    commands = json.loads((base / 'check_commands.json').read_text())
    mismatches = []
    checked = set()
    for record in commands:
        for rel, expected in record.get('input_sha256', {}).items():
            path = ROOT / rel
            if rel in checked:
                continue
            checked.add(rel)
            if not path.exists() or sha(path) != expected:
                mismatches.append(rel)
    drc = json.loads((base / 'drc.json').read_text())
    erc = json.loads((base / 'erc.json').read_text())
    return {'record': str(base.relative_to(ROOT)), 'input_files_checked': len(checked),
            'input_hash_mismatches': mismatches, 'version': drc['kicad_version'],
            'drc_date': drc['date'], 'erc_date': erc['date'],
            'DRC': len(drc['violations']), 'ERC': sum(len(s['violations']) for s in erc['sheets']),
            'unconnected': len(drc['unconnected_items']), 'parity': len(drc['schematic_parity']),
            'ignored_DRC': drc.get('ignored_checks'), 'ignored_ERC': erc.get('ignored_checks'),
            'rerun_in_this_review': False}


if __name__ == '__main__':
    result = {'tool': k.Version(), 'method_limits': 'Read-only PCB API; exact endpoint graph excludes zones, pad interiors and via vertical length. Path length is not an inductance or thermal model.',
              'boards': {}, 'existing_native_checks': {}}
    for kind, rev in [('power', 'P5R5'), ('motion', 'P5R5'), ('rear', 'P5R4'), ('imu', 'P5R4')]:
        result['boards'][kind] = board_inventory(kind, rev)
        result['existing_native_checks'][kind] = existing_checks(kind, rev)
    (HERE / 'native_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(HERE / 'native_audit.json'),
                      'existing_native_checks': result['existing_native_checks'],
                      'power_routes': {n: {k: v for k, v in r.items() if k != 'steps'}
                                       for n, r in result['boards']['power']['routes'].items()},
                      'diodes': {kind: {ref: p for ref, p in b['parts'].items() if ref.startswith('D')}
                                 for kind, b in result['boards'].items()},
                      'silk_counts': {kind: len(b['silkscreen']) for kind, b in result['boards'].items()}}, indent=2))
