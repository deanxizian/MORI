"""Narrow opt-in for moving a two-pad SMD resistor to the other outer face.

This does not permit fixed interfaces, pad/net edits or multilayer/cutout guard
reconstruction. Native DRC, reference and all old connections remain mandatory.
"""
import math
import pcbnew as pcb


def validate_side_change(board, footprint, guards, spec):
    side = spec.get('side_change')
    if side is None:
        return False
    old_face = board.GetLayerName(footprint.GetLayer())
    pads = list(footprint.Pads())
    if (not isinstance(side, dict)
            or set(side) != {'from_face', 'to_face', 'from_rotation_deg', 'axis', 'reason'}
            or side['from_face'] != old_face
            or {side['from_face'], side['to_face']} != {'F.Cu', 'B.Cu'}
            or side['from_rotation_deg'] != footprint.GetOrientationDegrees()
            or side['axis'] != 'LEFT_RIGHT' or not side['reason'].strip()
            or not footprint.GetReference().startswith('R')
            or len(pads) != 2 or {p.GetNumber() for p in pads} != {'1', '2'}
            or any(p.GetAttribute() != pcb.PAD_ATTRIB_SMD for p in pads)
            or not guards or spec.get('reconstruct_fixed_via_guards')
            or any(not z.GetIsRuleArea() or '_VIA_' in z.GetZoneName()
                   or list(z.GetLayerSet().Seq()) != [footprint.GetLayer()]
                   for z in guards)
            or not isinstance(spec.get('rotation_deg'), (int, float))
            or not math.isfinite(spec['rotation_deg'])):
        raise ValueError('Unsupported or incompletely declared resistor side change: '
                         + footprint.GetReference())
    return True
