"""Validate exact, bounded expansions of existing In2 power allocations.

No net, priority, fill, thermal, spacing or keepout setting can change. This is
geometry accounting; native refill, power regression and review remain required.
"""
import math

from shapely.geometry import Polygon, box

from copper_geometry import LAYERS, polyset


SETTING_GETTERS = (
    'GetIsRuleArea', 'GetZoneName', 'GetNetname', 'GetAssignedPriority',
    'GetDoNotAllowTracks', 'GetDoNotAllowVias', 'GetDoNotAllowPads',
    'GetDoNotAllowFootprints', 'GetDoNotAllowZoneFills', 'GetLocalClearance',
    'GetMinThickness', 'GetThermalReliefGap', 'GetThermalReliefSpokeWidth',
    'GetPadConnection', 'GetFillMode', 'GetIslandRemovalMode', 'GetMinIslandArea',
    'GetHatchGap', 'GetHatchThickness', 'GetHatchSmoothingLevel',
    'GetHatchSmoothingValue', 'GetHatchHoleMinArea', 'GetHatchBorderAlgorithm',
)


def zone_settings(board, zone):
    settings = {name: getattr(zone, name)() for name in SETTING_GETTERS}
    settings['hatch_orientation_degrees'] = zone.GetHatchOrientation().AsDegrees()
    settings['layers'] = [name for name in LAYERS
                          if zone.IsOnLayer(board.GetLayerID(name))]
    return settings


def zone_snapshot(board, zone):
    return {'settings': zone_settings(board, zone),
            'outline_wkt': polyset(zone.Outline()).wkt}


def expanded_zone_geometry(board, zone, spec):
    if zone_snapshot(board, zone) != spec.get('source_expected'):
        raise ValueError('Power-zone source snapshot mismatch')
    settings = zone_settings(board, zone)
    if (settings['GetIsRuleArea'] or settings['layers'] != ['In2.Cu']
            or settings['GetNetname'] in ('', 'GND')
            or settings['GetAssignedPriority'] <= 0 or settings['GetFillMode'] != 0):
        raise ValueError('Only an existing positive-priority solid In2 power allocation may expand')
    if not spec.get('reason', '').strip():
        raise ValueError('Power-zone expansion needs an explicit rationale')
    points = spec.get('union_patch_mm', [])
    if (len(points) < 3 or any(len(p) != 2 or any(
            not isinstance(v, (int, float)) or not math.isfinite(v) for v in p)
            for p in points)):
        raise ValueError('Power-zone patch needs finite polygon coordinates')
    patch = Polygon(points)
    if not patch.is_valid or patch.is_empty:
        raise ValueError('Power-zone patch is invalid')
    original = polyset(zone.Outline())
    target = original.union(patch)
    if target.geom_type != 'Polygon' or not target.is_valid or not target.covers(original):
        raise ValueError('Power-zone expansion must preserve one contiguous original allocation')
    bounds = board.GetBoardEdgesBoundingBox()
    envelope = box(bounds.GetX()/1e6, bounds.GetY()/1e6,
                   (bounds.GetX()+bounds.GetWidth())/1e6,
                   (bounds.GetY()+bounds.GetHeight())/1e6)
    if not envelope.covers(target):
        raise ValueError('Power-zone expansion extends outside the board bounds')
    added = target.area - original.area
    expected = spec.get('expected_added_area_mm2')
    if (not isinstance(expected, (int, float)) or not math.isfinite(expected)
            or expected <= 0 or added <= 1e-7 or abs(added-expected) > 1e-7):
        raise ValueError('Power-zone expansion area differs from the explicit plan')
    return target
