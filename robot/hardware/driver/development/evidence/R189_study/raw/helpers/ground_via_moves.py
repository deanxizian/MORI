"""Validate explicitly planned GND-via moves and their direct return paths.

This permits a reviewed layout operation, not a design-rule exemption. Every
source via keeps its UUID, net and padstack. Native refill, both reference-plane
contacts and the complete electrical regression remain separate requirements.
"""
import math
import pcbnew as pcb

from copper_geometry import Point, uid, xy, shape, via_snapshot


def finite_point(point):
    return (isinstance(point, (list, tuple)) and len(point) == 2
            and all(type(x) in (int, float) and math.isfinite(x) for x in point))


def walk(segments, start, end):
    """Require a continuous ordered path with no repeated intermediate vertex."""
    current, length, seen = tuple(start), 0., {tuple(start)}
    for a, b in segments:
        if not finite_point(a) or not finite_point(b):
            raise ValueError('Ground return has non-finite coordinates')
        if math.dist(current, a) <= 1e-6:
            nxt = tuple(b)
        elif math.dist(current, b) <= 1e-6:
            nxt = tuple(a)
        else:
            raise ValueError('Ground return path is not continuous')
        if math.dist(current, nxt) <= 1e-6 or nxt in seen:
            raise ValueError('Ground return has a zero segment or loop')
        length += math.dist(current, nxt)
        current = nxt
        seen.add(nxt)
    if not segments or math.dist(current, end) > 1e-6:
        raise ValueError('Ground return does not terminate at the declared via')
    return length


def validate_ground_via_moves(board, plan):
    specs = plan.get('move_ground_vias', [])
    if not specs:
        return []
    if not plan.get('board_sha256'):
        raise ValueError('Ground-via movement requires an exact source hash')
    items = {uid(t): t for t in board.GetTracks()}
    pads = {uid(p): p for f in board.GetFootprints() for p in f.Pads()}
    ids = [s['uuid'] for s in specs]
    conflicts = set(plan.get('delete_copper', []))
    for key in ['move_vias', 'reassign_vias', 'remove_obsolete_vias']:
        conflicts.update(s['uuid'] for s in plan.get(key, []))
    if len(ids) != len(set(ids)) or set(ids) & conflicts:
        raise ValueError('Duplicate or conflicting ground-via operation')
    moved_refs = {s['reference'] for s in plan.get('translations', [])}
    used_routes, reviews = set(), []
    for spec in specs:
        v = items.get(spec['uuid'])
        if (not isinstance(v, pcb.PCB_VIA) or v.GetNetname() != 'GND'
                or v.IsLocked() or via_snapshot(board, v) != spec['source_expected']):
            raise ValueError('Ground-via source snapshot/net/lock mismatch')
        point = spec['position_mm']
        if (not finite_point(point) or point == spec['source_expected']['position_mm']
                or not spec.get('reason', '').strip()):
            raise ValueError('Ground-via move needs a new finite position and reason')
        contacts = {uid(t) for t in items.values() if not isinstance(t, pcb.PCB_VIA)
                    and t.GetNetname() == 'GND'
                    and shape(t, t.GetLayer()).intersects(shape(v, t.GetLayer()))}
        declared = spec['source_contact_track_uuids']
        if len(declared) != len(set(declared)) or set(declared) != contacts:
            raise ValueError('Ground-via source contact inventory mismatch')
        restored, path_reviews = set(), []
        for path in spec['return_paths']:
            pad = pads.get(path['pad_uuid'])
            if (pad is None or pad.GetNetname() != 'GND'
                    or pad.GetParentFootprint().GetReference() in moved_refs):
                raise ValueError('Direct ground return needs an unchanged GND pad')
            source_ids = path['source_track_uuids']
            if (len(source_ids) != len(set(source_ids))
                    or not set(source_ids) <= set(plan.get('delete_copper', []))):
                raise ValueError('Direct return must explicitly replace its source tracks')
            source_segments, widths = [], []
            layer = board.GetLayerID(path['layer'])
            if path['layer'] not in ['F.Cu', 'B.Cu'] or not pad.IsOnLayer(layer):
                raise ValueError('Direct return requires its original pad face')
            for id_ in source_ids:
                t = items.get(id_)
                if (type(t).__name__ != 'PCB_TRACK' or t.GetNetname() != 'GND'
                        or t.GetLayer() != layer or t.IsLocked()):
                    raise ValueError('Unsupported direct ground-return source')
                source_segments.append((xy(t.GetStart()), xy(t.GetEnd())))
                widths.append(t.GetWidth()/1e6)
            # Some native traces begin inside a pad away from its centre.
            # Bind that actual exit explicitly; the pad copper must cover it.
            source_exit = path.get('source_pad_exit_mm', xy(pad.GetPosition()))
            if (not finite_point(source_exit)
                    or not shape(pad, layer).covers(Point(source_exit))):
                raise ValueError('Source ground-return exit is outside its pad copper')
            original_length = (math.dist(xy(pad.GetPosition()), source_exit)
                               + walk(source_segments, source_exit, xy(v.GetPosition())))
            indices = path['replacement_route_indices']
            if (len(indices) != len(set(indices)) or used_routes & set(indices)
                    or any(type(i) is not int or i < 0 or i >= len(plan.get('routes', [])) for i in indices)):
                raise ValueError('Invalid or shared ground-return route index')
            segments = []
            for index in indices:
                route = plan['routes'][index]
                if (route['net'] != 'GND' or route['layer'] != path['layer']
                        or type(route['width_mm']) not in (int, float)
                        or not math.isfinite(route['width_mm'])
                        or route['width_mm'] < max(widths)):
                    raise ValueError('Ground return changed net/face or narrowed copper')
                segments.extend(zip(route['points_mm'], route['points_mm'][1:]))
            new_length = walk(segments, xy(pad.GetPosition()), point)
            if new_length > original_length + 1e-6:
                raise ValueError('This operation cannot lengthen an existing direct ground return')
            restored.update(source_ids)
            used_routes.update(indices)
            path_reviews.append(dict(pad=pad.GetParentFootprint().GetReference()+'.'+pad.GetNumber(),
                                     layer=path['layer'],source_length_mm=original_length,
                                     source_pad_exit_mm=list(source_exit),
                                     planned_length_mm=new_length,minimum_width_mm=max(widths)))
        if not contacts <= restored:
            raise ValueError('Ground-via move leaves a direct source return undeclared')
        reviews.append(dict(uuid=spec['uuid'],direct_returns=path_reviews))
    return reviews
