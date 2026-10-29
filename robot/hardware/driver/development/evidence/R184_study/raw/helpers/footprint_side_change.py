"""Narrow opt-in for moving a supported two-pad SMD part to the other face.

This does not permit fixed interfaces, pad/net edits or multilayer/cutout guard
reconstruction. Native DRC, reference and all old connections remain mandatory.
Besides the existing resistor case, only D302's exact BAT54WS-7-F/SOD-323
definition is supported. Its cathode/anode net mapping must remain unchanged;
native footprint flipping is not a pin or polarity swap.
"""
import math
import pcbnew as pcb


def validate_side_change(board, footprint, guards, spec):
    side = spec.get('side_change')
    if side is None:
        return False
    old_face = board.GetLayerName(footprint.GetLayer())
    pads = list(footprint.Pads())
    supported_part = footprint.GetReference().startswith('R') or (
        footprint.GetReference() == 'D302'
        and footprint.GetValue() == 'BAT54WS-7-F'
        and footprint.GetFPIDAsString() == 'C3_Packages:D_SOD-323'
        and {p.GetNumber(): p.GetNetname() for p in pads}
        == {'1': '/FAULT_N', '2': '/CLR_N'})
    if (not isinstance(side, dict)
            or set(side) != {'from_face', 'to_face', 'from_rotation_deg', 'axis', 'reason'}
            or side['from_face'] != old_face
            or {side['from_face'], side['to_face']} != {'F.Cu', 'B.Cu'}
            or side['from_rotation_deg'] != footprint.GetOrientationDegrees()
            or side['axis'] != 'LEFT_RIGHT' or not side['reason'].strip()
            or not supported_part
            or len(pads) != 2 or {p.GetNumber() for p in pads} != {'1', '2'}
            or any(p.GetAttribute() != pcb.PAD_ATTRIB_SMD for p in pads)
            or not guards or spec.get('reconstruct_fixed_via_guards')
            or any(not z.GetIsRuleArea() or '_VIA_' in z.GetZoneName()
                   or list(z.GetLayerSet().Seq()) != [footprint.GetLayer()]
                   for z in guards)
            or not isinstance(spec.get('rotation_deg'), (int, float))
            or not math.isfinite(spec['rotation_deg'])):
        raise ValueError('Unsupported or incompletely declared SMD side change: '
                         + footprint.GetReference())
    return True
