"""Apply an explicit plan to a NEW directory; never overwrite a prior trial.

Saves only the candidate PCB, with deterministic new item UUIDs. Copies source
schematics, libraries and rules without modification. No devices or fabrication.
"""
import argparse
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path
import pcbnew as pcb
from shapely.affinity import translate, rotate, scale
from shapely.ops import unary_union
from copper_geometry import parts, polyset, xy, via_snapshot, via_contact_layers
from zone_expansion import expanded_zone_geometry, zone_settings
from footprint_side_change import validate_side_change


def point_mm(position):
    """Round decimal millimetres to KiCad's integer nanometre grid.

    pcb.FromMM truncates some binary floats (32.3 becomes 32.299999 mm),
    breaking exact planned via centres after save/reload.
    """
    return pcb.VECTOR2I(*(int(round(value * 1_000_000)) for value in position))


def set_outline(zone, geometry):
    if len(parts(geometry)) != 1:
        raise ValueError('A native rule area must have one contiguous outline; split or merge explicitly')
    outline = zone.Outline()
    outline.RemoveAllContours()
    for polygon in parts(geometry):
        index = outline.NewOutline()
        for x, y in list(polygon.exterior.coords)[:-1]:
            outline.Append(int(round(x * 1e6)), int(round(y * 1e6)), index)
        for ring in polygon.interiors:
            hole = outline.NewHole(index)
            for x, y in list(ring.coords)[:-1]:
                outline.Append(int(round(x * 1e6)), int(round(y * 1e6)), index, hole)


def move_body_guards(owned, delta_mm, reconstruct, rotation_delta=0, origin_mm=None,
                     rotate_fixed_cutouts=False):
    """Move component guards while keeping their existing via cutouts fixed.

    Explicit opt-in only. Every original zone UUID and restriction flag remains.
    New via exclusion is exactly moved body minus original fixed cutouts. This
    is a changed keepout geometry requiring explicit review, not an exemption
    from the strict candidate audit.
    """
    delta = point_mm(delta_mm)
    active_vias = [z for z in owned if z.GetDoNotAllowVias()]
    if rotate_fixed_cutouts and not reconstruct:
        raise ValueError('Fixed-cutout rotation requires explicit guard reconstruction')
    if rotation_delta and reconstruct and not rotate_fixed_cutouts:
        raise ValueError('Rotation with fixed-via cutouts requires explicit rotate_fixed_via_guards')
    def transformed(g):
        return translate(rotate(g, -rotation_delta, origin=origin_mm) if rotation_delta else g,
                         xoff=delta_mm[0], yoff=delta_mm[1])
    if reconstruct:
        bodies = [z for z in owned if z.GetDoNotAllowTracks()]
        if not bodies or not active_vias or any(z.GetDoNotAllowTracks() for z in active_vias):
            raise ValueError('Guard reconstruction requires separate body and via-only guards')
        body = unary_union([polyset(z.Outline()) for z in bodies])
        old_via_union = unary_union([polyset(z.Outline()) for z in active_vias])
        if old_via_union.difference(body).area > 1e-8:
            raise ValueError('Via guards extend outside owned body; dedicated review required')
        fixed_holes = body.difference(old_via_union)
        moved_body = transformed(body)
        target = moved_body.difference(fixed_holes)
        rewritten = {z.m_Uuid.AsString(): transformed(polyset(z.Outline())).difference(fixed_holes)
                     for z in active_vias}
        missing = target.difference(unary_union(list(rewritten.values())))
        # KiCad serializes one outline for a rule area. Fill each vacated
        # cutout strip into an adjacent existing zone, never a remote island
        # that would silently disappear on SaveBoard/reload.
        for piece in parts(missing):
            if piece.area < 1e-10:
                continue
            for id_, region in rewritten.items():
                combined = region.union(piece)
                if len(parts(combined)) == 1:
                    rewritten[id_] = combined
                    break
            else:
                raise ValueError('Vacated cutout has no adjacent native via guard')
        for z in owned:
            id_ = z.m_Uuid.AsString()
            if id_ in rewritten:
                if rewritten[id_].is_empty:
                    raise ValueError('Move empties a guard; dedicated reconstruction required')
                set_outline(z, rewritten[id_])
            else:
                if rotation_delta:
                    z.Rotate(point_mm(origin_mm),
                             pcb.EDA_ANGLE(rotation_delta, pcb.DEGREES_T))
                z.Move(delta)
        actual = unary_union([polyset(z.Outline()) for z in active_vias])
        if actual.symmetric_difference(target).area > 1e-7:
            raise ValueError('Rebuilt guard geometry does not match exact target')
        return {'method': 'Rigidly transformed native body minus unchanged native via cutouts',
                'rotation_delta_deg': rotation_delta,
                'fixed_cutouts_mm': [list(p.bounds) for p in parts(fixed_holes)],
                'fixed_cutout_area_mm2': fixed_holes.area,
                'new_via_guard_area_mm2': actual.area}
    for z in owned:
        if rotation_delta:
            z.Rotate(point_mm(origin_mm),
                     pcb.EDA_ANGLE(rotation_delta, pcb.DEGREES_T))
        z.Move(delta)
    return None


def build(source, destination, plan_file):
    plan = json.loads(Path(plan_file).read_text())
    source, destination = Path(source), Path(destination)
    if plan.get('board_sha256') and hashlib.sha256((source/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest() != plan['board_sha256']:
        raise ValueError('Plan source PCB hash does not match')
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('*.kicad_prl', '*.lck'))
    path = destination / 'MORI_Interface_C3.kicad_pcb'
    board = pcb.LoadBoard(str(path))
    nets = {n.GetNetname(): n for n in board.GetNetInfo().NetsByNetcode().values()}
    byid = {o.m_Uuid.AsString(): o for o in board.GetTracks()}
    changes = []
    zone_expansions = plan.get('power_zone_expansions', [])
    zone_ids = [s['uuid'] for s in zone_expansions]
    if len(zone_ids) != len(set(zone_ids)) or (zone_ids and not plan.get('board_sha256')):
        raise ValueError('Unique power-zone expansions require an exact source board hash')
    zones = {z.m_Uuid.AsString(): z for z in board.Zones()}
    expanded_zones = {}
    for spec in zone_expansions:
        zone = zones.get(spec['uuid'])
        if zone is None:
            raise ValueError('Missing power zone: ' + spec['uuid'])
        geometry = expanded_zone_geometry(board, zone, spec)
        expanded_zones[spec['uuid']] = (geometry, zone_settings(board, zone))
        set_outline(zone, geometry)
        changes.append({'kind': 'power_zone_expansion', **spec})
    # Explicit transforms of parts and their own BODY guards. A side change is
    # separately declared and restricted to two-pad SMD resistors/simple guards.
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    forbidden = {'J101', 'J102', 'J105'}
    refs = [s['reference'] for s in plan.get('translations', [])]
    if len(refs) != len(set(refs)):
        raise ValueError('Duplicate footprint transform')
    for spec in plan.get('translations', []):
        ref = spec['reference']
        if ref in forbidden or ref.startswith(('J', 'H')):
            raise ValueError('Mechanical-interface translation is not supported: ' + ref)
        f = fps[ref]
        actual = [f.GetPosition().x / 1e6, f.GetPosition().y / 1e6]
        if actual != spec['from_mm']:
            raise ValueError('Source position mismatch: ' + ref)
        owned = [z for z in board.Zones() if z.GetIsRuleArea()
                 and z.GetZoneName().startswith('BODY_' + ref + '_')]
        reconstruct = spec.get('reconstruct_fixed_via_guards', False)
        if any('_VIA_' in z.GetZoneName() for z in owned) and not reconstruct:
            raise ValueError('BODY guard contains fixed-via cutouts; explicit regeneration required: ' + ref)
        delta = point_mm(spec['delta_mm'])
        old_angle = f.GetOrientationDegrees()
        new_angle = spec.get('rotation_deg', old_angle)
        side_change = validate_side_change(board, f, owned, spec)
        if side_change:
            if not plan.get('board_sha256'):
                raise ValueError('Side change requires an exact source PCB hash')
            f.Flip(f.GetPosition(), pcb.FLIP_DIRECTION_LEFT_RIGHT)
            flipped_angle = f.GetOrientationDegrees()
            for z in owned:
                mirrored = scale(polyset(z.Outline()), xfact=-1, yfact=1, origin=tuple(actual))
                target = translate(rotate(mirrored, -(new_angle-flipped_angle), origin=actual),
                                   xoff=spec['delta_mm'][0], yoff=spec['delta_mm'][1])
                set_outline(z, target)
                z.SetLayer(board.GetLayerID(spec['side_change']['to_face']))
        f.SetOrientationDegrees(new_angle)
        f.Move(delta)
        guard_review = ({'method': 'Left-right mirror, then rigid rotation/translation; outer guard face swapped',
                         'side_change': spec['side_change']} if side_change else
                        move_body_guards(owned, spec['delta_mm'], reconstruct, new_angle-old_angle,
                                         actual, spec.get('rotate_fixed_via_guards', False)))
        guards = [z.m_Uuid.AsString() for z in owned]
        if not guards:
            raise ValueError('No owned BODY guards for translated part: ' + ref)
        changes.append({'kind': 'footprint_side_change' if side_change else
                        ('footprint_transform' if new_angle!=old_angle else 'footprint_translation'),
                        **spec, 'source_rotation_deg':old_angle,'translated_body_guards': guards,
                        'guard_reconstruction': guard_review})
    deletions = plan.get('delete_copper', [])
    snapshots = plan.get('deleted_copper_expected', {})
    if len(deletions) != len(set(deletions)) or set(snapshots) != set(deletions):
        raise ValueError('Every explicitly deleted track needs one exact source snapshot')
    for id_ in deletions:
        if id_ not in byid:
            raise ValueError('Missing copper UUID ' + id_)
        item, expected = byid[id_], snapshots[id_]
        if type(item).__name__ != 'PCB_TRACK':
            raise ValueError('Only explicitly replaced straight tracks may be deleted: ' + id_)
        actual = {'net':item.GetNetname(),'layer':board.GetLayerName(item.GetLayer()),
                  'width_mm':item.GetWidth()/1e6,'start_mm':list(xy(item.GetStart())),
                  'end_mm':list(xy(item.GetEnd()))}
        if actual != expected:
            raise ValueError('Deleted source track snapshot mismatch: ' + id_)
        changes.append({'uuid':id_,'kind':'removed_track',**actual})
        board.Remove(item)
    reassignments = plan.get('reassign_vias', [])
    via_moves = plan.get('move_vias', [])
    move_ids = {s['uuid'] for s in via_moves}
    if (len(move_ids) != len(via_moves)
            or move_ids & (set(deletions) | {s['uuid'] for s in reassignments})):
        raise ValueError('Duplicate or conflicting via move')
    if via_moves and not plan.get('board_sha256'):
        raise ValueError('Via movement requires an exact source board hash')
    obsolete_vias = plan.get('remove_obsolete_vias', [])
    obsolete_ids = {s['uuid'] for s in obsolete_vias}
    if obsolete_vias and not plan.get('board_sha256'):
        raise ValueError('Obsolete via removal requires an exact source board hash')
    if (len(obsolete_ids) != len(obsolete_vias)
            or obsolete_ids & (set(deletions) | {s['uuid'] for s in reassignments} | move_ids)):
        raise ValueError('Duplicate or conflicting obsolete via operation')
    for spec in obsolete_vias:
        v = byid.get(spec['uuid'])
        if (not isinstance(v, pcb.PCB_VIA) or v.GetNetname() == 'GND'
                or via_snapshot(board, v) != spec['source_expected']):
            raise ValueError('Obsolete non-ground via snapshot mismatch: ' + spec['uuid'])
        contacts = via_contact_layers(board, v)
        if (len(contacts) > 1 or contacts != spec['remaining_contact_layers']
                or not spec.get('reason', '').strip()):
            raise ValueError('Via still transfers between layers or lacks an exact removal rationale: ' + spec['uuid'])
        changes.append({'kind': 'removed_obsolete_via', **spec})
        board.Remove(v)
    if reassignments and not plan.get('board_sha256'):
        raise ValueError('Via reuse requires an exact source board hash')
    if len({s['uuid'] for s in reassignments}) != len(reassignments):
        raise ValueError('Duplicate via reassignment')
    for spec in reassignments:
        v = byid.get(spec['uuid'])
        if not isinstance(v, pcb.PCB_VIA) or via_snapshot(board, v) != spec['source_expected']:
            raise ValueError('Reused via source snapshot mismatch: ' + spec['uuid'])
        if spec['net'] not in nets or spec['net'] == v.GetNetname() or 'GND' in [spec['net'], v.GetNetname()]:
            raise ValueError('Via reassignment must be between two distinct existing non-ground nets')
        v.SetNet(nets[spec['net']])
        if 'position_mm' in spec:
            pos = spec['position_mm']
            if len(pos) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in pos):
                raise ValueError('Reused via needs two finite position coordinates')
            v.SetPosition(point_mm(pos))
        changes.append({'kind': 'via_reassignment_and_move' if 'position_mm' in spec else 'via_net_reassignment', **spec})
    for spec in via_moves:
        v = byid.get(spec['uuid'])
        if (not isinstance(v, pcb.PCB_VIA) or v.GetNetname() == 'GND'
                or via_snapshot(board, v) != spec['source_expected']):
            raise ValueError('Moved non-ground via snapshot mismatch: ' + spec['uuid'])
        pos = spec['position_mm']
        if (len(pos) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in pos)
                or pos == spec['source_expected']['position_mm'] or not spec.get('reason', '').strip()):
            raise ValueError('Via move requires a distinct finite position and explicit rationale')
        v.SetPosition(point_mm(pos))
        changes.append({'kind': 'via_position_move', **spec})
    def vec(pos):
        return point_mm(pos)
    for i, spec in enumerate(plan.get('vias', [])):
        v = pcb.PCB_VIA(board)
        v.SetPosition(vec(spec['position_mm']))
        v.SetViaType(pcb.VIATYPE_THROUGH)
        v.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
        v.SetWidth(pcb.FromMM(spec.get('diameter_mm', .5)))
        v.SetDrill(pcb.FromMM(spec.get('drill_mm', .3)))
        v.SetNet(nets[spec['net']])
        v.SetUuid(pcb.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL, plan['revision'] + '/via/' + str(i)))))
        board.Add(v)
        changes.append({'uuid': v.m_Uuid.AsString(), 'kind': 'via', **spec})
    for i, spec in enumerate(plan.get('routes', [])):
        for j, (a, b) in enumerate(zip(spec['points_mm'], spec['points_mm'][1:])):
            t = pcb.PCB_TRACK(board)
            t.SetStart(vec(a)); t.SetEnd(vec(b))
            t.SetWidth(pcb.FromMM(spec['width_mm']))
            t.SetLayer(board.GetLayerID(spec['layer']))
            t.SetNet(nets[spec['net']])
            t.SetUuid(pcb.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL, plan['revision'] + '/route/' + str(i) + '/' + str(j)))))
            board.Add(t)
            changes.append({'uuid': t.m_Uuid.AsString(), 'kind': 'track', 'net': spec['net'],
                            'layer':spec['layer'], 'width_mm':spec['width_mm'], 'start_mm':a, 'end_mm':b})
    board.GetTitleBlock().SetRevision('C3_' + plan['revision'] + '_PROTOTYPE')
    pcb.SaveBoard(str(path), board)
    readback = pcb.LoadBoard(str(path))
    saved_zones = {z.m_Uuid.AsString(): z for z in readback.Zones()}
    expected_zones = {z.m_Uuid.AsString(): z for z in board.Zones()}
    saved_tracks = {t.m_Uuid.AsString(): t for t in readback.GetTracks()}
    for id_, (geometry, settings) in expanded_zones.items():
        zone = saved_zones.get(id_)
        if (zone is None or zone_settings(readback, zone) != settings
                or polyset(zone.Outline()).symmetric_difference(geometry).area > 1e-7):
            raise ValueError('Saved/reloaded power zone differs from the explicit plan: ' + id_)
    if obsolete_ids & set(saved_tracks):
        raise ValueError('An explicitly obsolete via survived save/reload')
    for spec in reassignments:
        expected = {**spec['source_expected'], 'net': spec['net']}
        if 'position_mm' in spec:
            expected['position_mm'] = spec['position_mm']
        if via_snapshot(readback, saved_tracks[spec['uuid']]) != expected:
            raise ValueError('Saved/reloaded reused via differs from explicit plan: ' + spec['uuid'])
    for spec in via_moves:
        expected = {**spec['source_expected'], 'position_mm': spec['position_mm']}
        if via_snapshot(readback, saved_tracks[spec['uuid']]) != expected:
            raise ValueError('Saved/reloaded moved via differs from explicit plan: ' + spec['uuid'])
    for change in changes:
        for id_ in change.get('translated_body_guards', []):
            if id_ not in saved_zones or polyset(expected_zones[id_].Outline()).symmetric_difference(
                    polyset(saved_zones[id_].Outline())).area > 1e-7 or (
                    zone_settings(board, expected_zones[id_]) != zone_settings(readback, saved_zones[id_])):
                raise ValueError('Saved/reloaded body guard differs from the explicit plan: ' + id_)
    (destination / 'edit_plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (destination / 'edit_manifest.json').write_text(json.dumps(changes, indent=2)+'\n')
    print(json.dumps({'candidate':str(destination),'added':len(changes)}))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');p.add_argument('plan');a=p.parse_args();build(a.source,a.destination,a.plan)
