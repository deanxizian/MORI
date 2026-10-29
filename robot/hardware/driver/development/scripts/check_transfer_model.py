"""Read-only cross-check against the received header padstack and native fill.

This checks a routing/audit model, not electrical or manufacturing qualification.
Run with the isolated KiCad Python; never saves the source board.
"""
import argparse
import json
import math
from pathlib import Path
from copper_geometry import *


def check(board):
    c = Copper(board)
    pads = {c.pad_name(p): p for p in c.pads}
    pad = pads['J102.7']
    ref = 'In4.Cu'
    transfer = reference_transfer_shape(c, pad, ref)
    radius = xy(pad.GetDrillSize())[0] / 2
    clearance = inner_zone_clearance(c.path)
    actual = Point(xy(pad.GetPosition())).distance(c.copper['GND', ref])
    npth = [p for p in c.pads if p.GetAttribute() == pcb.PAD_ATTRIB_NPTH]
    checks = {
        'received_1p02_mm_circular_PTH': xy(pad.GetDrillSize()) == (1.02, 1.02),
        'unused_reference_annulus_not_flashed': not pad.FlashLayer(c.ids[ref]),
        'transfer_uses_barrel_not_external_land': transfer is not None and
            abs(math.sqrt(transfer.area / math.pi) - radius) < .001,
        'native_fill_matches_barrel_plus_rule': abs(actual - radius - clearance) < .002,
        'SMD_has_no_plated_transfer': reference_transfer_shape(c, pads['D302.1'], ref) is None,
        'four_NPTH_have_no_plated_transfer': len(npth) == 4 and all(
            reference_transfer_shape(c, p, ref) is None for p in npth),
    }
    return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
            'board_sha256': c.sha, 'pad_uuid': uid(pad), 'pad': 'J102.7',
            'external_pad_mm': xy(pad.GetSize()), 'drill_mm': xy(pad.GetDrillSize()),
            'native_reference_distance_mm': actual, 'R17_clearance_mm': clearance,
            'scope': 'Native geometry/model cross-check only; same-net surface-island membership is separately enforced by the auditor.',
            'manufacturing_release': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('board')
    parser.add_argument('output')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = check(args.board)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
