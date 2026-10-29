"""Read-only INA300 RLIMIT return-path screen using saved native copper.

TI SBOS613C section 10.1 (printed page 29) requires a direct RLIMIT return
to the device ground terminal, including when a layer transition is needed.
Whole-net continuity through a ground plane alone does not establish this.

This is a necessary-path screen, not complete manufacturer-layout approval:
an explicit path still needs review for length, branching/plane contacts,
loop area, capacitance, coupling, reference continuity and physical behavior.
The board must already have current native fills. No files are modified.
"""
import argparse
import copy
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from copper_geometry import Copper, ERROR_MM, GeometryCollection, parts, pcb, uid, unary_union, xy


def audit(board_path):
    board_path = Path(board_path)
    before = hashlib.sha256(board_path.read_bytes()).hexdigest()
    c = Copper(board_path)
    footprints = {f.GetReference(): f for f in c.footprints}
    device = footprints['U1701']
    if (device.GetValue() != 'INA300AIDGSR'
            or str(device.GetFPID().GetLibItemName()) != 'TI_DGS0010A'):
        raise ValueError('Unreviewed INA300 device/package; verify the ground pin map first')

    def pad(name):
        matches = [p for p in c.pads if c.pad_name(p) == name]
        if len(matches) != 1:
            raise ValueError('Expected one native pad: ' + name)
        return matches[0]

    ground = pad('U1701.8')
    resistor = pad('R1701.1')
    bypass = pad('C1701.2')
    if any(p.GetNetname() != 'GND' for p in (ground, resistor, bypass)):
        raise ValueError('Reviewed INA300 ground terminals changed net')
    if pad('R1701.2').GetNetname() != pad('U1701.3').GetNetname():
        raise ValueError('R1701 is no longer on the reviewed LIMIT terminal')

    # Keep the loaded board and all cached native shapes shared/read-only.
    # Only this copy's in-memory copper unions omit zone fills. Native via
    # barrels/pads still join their actual flashed layers via connected_pairs.
    native = defaultdict(list)
    for (item_id, layer), shape in c.shapes.items():
        native[c.by_id[item_id].GetNetname(), layer].append(shape)
    trace_only = copy.copy(c)
    trace_only.__dict__['copper'] = {key: unary_union(items) for key, items in native.items()}
    full_pairs = c.connected_pairs('GND')
    trace_pairs = trace_only.connected_pairs('GND')

    def row(start, end):
        pair = tuple(sorted((uid(start), uid(end))))
        face = c.pad_faces[uid(start)]
        same_face = face == c.pad_faces[uid(end)]
        lands = [c.shapes.get((uid(p), face), GeometryCollection()) for p in (start, end)]
        face_connected = same_face and all(not land.is_empty for land in lands) and any(
            all(region.intersects(land) for land in lands)
            for region in parts(c.copper.get(('GND', face), GeometryCollection())))
        path_ids = {uid(start)} | {
            b if a == uid(start) else a for a, b in trace_pairs if uid(start) in (a, b)}
        return {
            'from': c.pad_name(start), 'to': c.pad_name(end),
            'native_pad_uuids': [uid(start), uid(end)],
            'mounted_faces': [c.pad_faces[uid(start)], c.pad_faces[uid(end)]],
            'full_native_copper_connected': pair in full_pairs,
            'same_mounted_face_filled_component': bool(face_connected),
            'explicit_track_pad_via_path_without_fills': pair in trace_pairs,
            'source_explicit_component_pads': sorted(
                c.pad_name(p) for p in c.pads if uid(p) in path_ids),
            'source_explicit_component_vias': [
                {'uuid': uid(v), 'position_mm': list(xy(v.GetPosition()))}
                for v in c.vias if uid(v) in path_ids],
        }

    limit = row(resistor, ground)
    control = row(bypass, ground)
    if not limit['full_native_copper_connected']:
        status, reason = 'FAIL', 'RLIMIT ground is electrically disconnected.'
    elif limit['explicit_track_pad_via_path_without_fills']:
        status, reason = 'PASS', 'Explicit path exists; full layout review remains required.'
    elif limit['same_mounted_face_filled_component']:
        status, reason = 'NOT_TESTED', 'Same-face filled copper requires manual direct-return review.'
    else:
        status, reason = 'FAIL', 'Connection depends on plane fills; no direct return to U1701.8 was found.'
    assert hashlib.sha256(board_path.read_bytes()).hexdigest() == before
    return {
        'scope': __doc__, 'board_sha256': before,
        'datasheet': {'url': 'https://www.ti.com/lit/ds/symlink/ina300.pdf',
                      'document': 'SBOS613C', 'revision': 'June 2021',
                      'section': '10.1', 'printed_pages': [29, 30]},
        'device': 'INA300AIDGSR / DGS VSSOP-10',
        'ground_terminal': 'U1701.8',
        'latch_terminal_is_not_ground_terminal': 'U1701.6',
        'geometry_polygon_error_max_mm': ERROR_MM,
        'rlimit_return': limit,
        'bypass_return_positive_control': control,
        'direct_return_screen': status, 'reason': reason,
        'manufacturer_layout_qualification': 'NOT_TESTED',
        'physical': 'NOT_TESTED', 'manufacturing_release': False,
        'board_bytes_unchanged': True,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board')
    parser.add_argument('output')
    args = parser.parse_args()
    result = audit(args.board)
    with Path(args.output).open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in
                     ('board_sha256', 'direct_return_screen', 'reason', 'board_bytes_unchanged')}))
