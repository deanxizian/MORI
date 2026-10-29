"""Validate explicit placement and copper changes without hiding strict audit failures.

The ordinary audit intentionally reports moved pads/guards as FAIL. This separate
review proves those differences equal the recorded plan, checks unchanged items,
and requires every electrical regression to pass. It does not approve visuals,
component selection, thermal behavior, EMC or manufacturing.
"""
import argparse
import json
import uuid
from pathlib import Path
from shapely.affinity import translate, rotate

from copper_geometry import *
from zone_expansion import expanded_zone_geometry, zone_settings


def review(source, candidate, plan_path, regression_path, source_regression_path):
    a, b = Copper(source), Copper(candidate)
    plan = json.loads(Path(plan_path).read_text())
    reg = json.loads(Path(regression_path).read_text())
    old_reg = json.loads(Path(source_regression_path).read_text())
    errors, checks = [], {}
    def check(name, ok):
        checks[name] = bool(ok)
        if not ok:
            errors.append(name)
    check('plan_source_hash', plan['board_sha256'] == a.sha)
    check('regression_hashes', reg['baseline_sha256'] == a.sha and reg['board_sha256'] == b.sha)
    check('source_regression_hash', old_reg['board_sha256'] == a.sha)
    check('six_layers_and_thickness', a.board.GetCopperLayerCount() == b.board.GetCopperLayerCount() == 6
          and a.board.GetDesignSettings().GetBoardThickness() == b.board.GetDesignSettings().GetBoardThickness())
    moves = {s['reference']: s for s in plan.get('translations', [])}
    # remove_unused_layers is dynamic: attaching to an existing plated hole can
    # restore its native land on that layer. Only an explicit, exact-centre
    # connection may account for that copper delta; pad definitions stay fixed.
    activation_rows = plan.get('activate_pth_layers', [])
    activations = {(s.get('pad_uuid'), s.get('layer')): s for s in activation_rows}
    check('unique_pth_activations', len(activations) == len(activation_rows))
    activated_pad_ids = set()
    pth_return_reviews = []
    for (id_, layer), spec in activations.items():
        p, q = a.by_id.get(id_), b.by_id.get(id_)
        ok = isinstance(p, pcb.PAD) and isinstance(q, pcb.PAD) and layer in ['In2.Cu', 'In3.Cu']
        if ok:
            dx, dy = xy(p.GetDrillSize())
            ok &= (p.GetAttribute() == q.GetAttribute() == pcb.PAD_ATTRIB_PTH
                   and p.GetDrillShape() == q.GetDrillShape() == pcb.PAD_DRILL_SHAPE_CIRCLE
                   and dx > 0 and abs(dx-dy) < 1e-8
                   and p.IsOnLayer(a.ids[layer]) and q.IsOnLayer(b.ids[layer])
                   and not p.FlashLayer(a.ids[layer]) and q.FlashLayer(b.ids[layer])
                   and spec.get('source_flashed') is False
                   and spec.get('pad') == a.pad_name(p)
                   and spec.get('position_mm') == list(xy(p.GetPosition()))
                   and xy(p.GetPosition()) == xy(q.GetPosition()))
            ok &= layer != 'In2.Cu' or p.GetNetname() in in2_routing_nets(source)
            ok &= any(r['net'] == p.GetNetname() and r['layer'] == layer
                      and list(xy(p.GetPosition())) in [r['points_mm'][0], r['points_mm'][-1]]
                      for r in plan.get('routes', []))
        check('pth_activation_' + str(id_) + '_' + str(layer), ok)
        if not ok:
            continue
        activated_pad_ids.add(id_)
        touched = [ly for ly in REFERENCE if (id_, ly) in b.shapes
                   and any(t.GetNetname() == q.GetNetname()
                           and b.board.GetLayerName(t.GetLayer()) == ly
                           and b.shapes[id_, ly].intersects(b.shapes[uid(t), ly])
                           for t in b.segments)]
        references = sorted({REFERENCE[ly] for ly in touched})
        ground = [g for g in b.pads + b.vias if g.GetNetname() == 'GND'
                  and all((uid(g), ref) in b.shapes and b.shapes[uid(g), ref].intersects(
                      b.copper.get(('GND', ref), GeometryCollection())) for ref in ['In1.Cu', 'In4.Cu'])]
        nearest = min((Point(xy(q.GetPosition())).distance(Point(xy(g.GetPosition())))
                       for g in ground), default=None)
        return_ok = len(references) <= 1 or (nearest is not None and nearest <= 2)
        check('pth_reference_transition_' + id_ + '_' + layer, return_ok)
        pth_return_reviews.append(dict(pad=a.pad_name(p), activated_layer=layer,
                                       track_contact_layers=touched, reference_layers=references,
                                       nearest_dual_plane_ground_mm=nearest,
                                       status='NOT_APPLICABLE' if len(references) <= 1 else ('PASS' if return_ok else 'FAIL'),
                                       limits='Project 2 mm screen only; external connector/module return path and EMC not qualified.'))
    af, bf = {f.GetReference(): f for f in a.footprints}, {f.GetReference(): f for f in b.footprints}
    check('same_footprint_set', set(af) == set(bf))
    moved_pad_ids, moved_guard_ids = set(), set()
    for ref, old in af.items():
        new = bf[ref]
        spec = moves.get(ref)
        delta = spec['delta_mm'] if spec else [0, 0]
        rotation = spec.get('rotation_deg',old.GetOrientationDegrees()) if spec else old.GetOrientationDegrees()
        rotation_delta = rotation-old.GetOrientationDegrees()
        check('footprint_' + ref, all(abs(x+y-z) < 1e-6 for x,y,z in zip(xy(old.GetPosition()), delta, xy(new.GetPosition())))
              and abs((rotation-new.GetOrientationDegrees()+180) % 360-180) < 1e-6
              and old.GetLayer() == new.GetLayer()
              and old.GetValue() == new.GetValue() and old.GetFPID().GetUniStringLibId() == new.GetFPID().GetUniStringLibId())
        if spec:
            check('translation_source_' + ref, list(xy(old.GetPosition())) == spec['from_mm'])
        for p in old.Pads():
            q = b.by_id.get(uid(p))
            ok = q is not None and p.GetNumber() == q.GetNumber() and p.GetNetname() == q.GetNetname()
            ok = ok and xy(p.GetSize()) == xy(q.GetSize()) and xy(p.GetDrillSize()) == xy(q.GetDrillSize())
            ok = ok and p.GetAttribute() == q.GetAttribute() and p.GetDrillShape() == q.GetDrillShape()
            ok = ok and list(p.GetLayerSet().Seq()) == list(q.GetLayerSet().Seq())
            if ok:
                for layer in LAYERS:
                    if p.IsOnLayer(a.ids[layer]):
                        # Check even unflashed native padstack geometry. An
                        # activation must not conceal a size/shape edit.
                        expected_definition = translate(rotate(shape(p, a.ids[layer]),
                            -rotation_delta, origin=xy(old.GetPosition())), xoff=delta[0], yoff=delta[1])
                        ok &= expected_definition.symmetric_difference(shape(q, b.ids[layer])).area < 1e-7
                    before = a.shapes.get((uid(p),layer), GeometryCollection())
                    if (uid(p), layer) in activations:
                        before = shape(p, a.ids[layer])
                    expected = translate(rotate(before,-rotation_delta,origin=xy(old.GetPosition())), xoff=delta[0], yoff=delta[1])
                    actual = b.shapes.get((uid(p),layer), GeometryCollection())
                    ok &= expected.symmetric_difference(actual).area < 1e-7
            check('pad_' + uid(p), ok)
            if spec:
                moved_pad_ids.add(uid(p))
    az, bz = {uid(z):z for z in a.zones}, {uid(z):z for z in b.zones}
    check('same_zone_set', set(az) == set(bz))
    expansion_rows = plan.get('power_zone_expansions', [])
    expansion_specs = {s['uuid']:s for s in expansion_rows}
    check('unique_power_zone_expansions', len(expansion_specs) == len(expansion_rows))
    expanded_zones = {}
    for id_, spec in expansion_specs.items():
        try:
            expanded_zones[id_] = expanded_zone_geometry(a.board, az[id_], spec)
            ok = id_ in bz
        except (ValueError, KeyError, TypeError):
            ok = False
        check('power_zone_source_and_patch_' + id_, ok)
    ak, bk = {k['id']:k for k in a.keepouts}, {k['id']:k for k in b.keepouts}
    for ref, spec in moves.items():
        old = [k for k in a.keepouts if k['name'].startswith('BODY_' + ref + '_')]
        moved_guard_ids.update(k['id'] for k in old)
        body = unary_union([k['shape'] for k in old if k['tracks']])
        via = unary_union([k['shape'] for k in old if k['vias']])
        delta = spec['delta_mm']
        rotation_delta=spec.get('rotation_deg',af[ref].GetOrientationDegrees())-af[ref].GetOrientationDegrees()
        if spec.get('reconstruct_fixed_via_guards'):
            check('explicit_fixed_cutout_rotation_' + ref,
                  rotation_delta == 0 or spec.get('rotate_fixed_via_guards') is True)
            expected = translate(rotate(body,-rotation_delta,origin=xy(af[ref].GetPosition())),
                                 xoff=delta[0],yoff=delta[1]).difference(body.difference(via))
            actual = unary_union([bk[k['id']]['shape'] for k in old if k['vias']])
            check('fixed_via_cutouts_' + ref, expected.symmetric_difference(actual).area < 1e-7)
        for k in old:
            if k['vias'] and spec.get('reconstruct_fixed_via_guards'):
                continue
            expected = translate(rotate(k['shape'],-rotation_delta,origin=xy(af[ref].GetPosition())),xoff=delta[0],yoff=delta[1])
            check('moved_guard_' + k['id'], expected.symmetric_difference(bk[k['id']]['shape']).area < 1e-7)
    for id_, z in az.items():
        q = bz[id_]
        ok = zone_settings(a.board, z) == zone_settings(b.board, q)
        if id_ not in moved_guard_ids:
            expected = expanded_zones.get(id_, polyset(z.Outline()))
            ok &= expected.symmetric_difference(polyset(q.Outline())).area < 1e-7
        check('zone_constraints_' + id_, ok)
    changed_allocations = {id_ for id_, z in az.items() if not z.GetIsRuleArea()
                           and polyset(z.Outline()).symmetric_difference(polyset(bz[id_].Outline())).area > 1e-7}
    check('exact_power_zone_expansion_set', changed_allocations == set(expansion_specs))
    # Replacement requires exact source snapshots; every other copper object
    # remains frozen. Merely moving a part does not excuse deleting its traces.
    deletions = plan.get('delete_copper', [])
    snapshots = plan.get('deleted_copper_expected', {})
    reassignments = plan.get('reassign_vias', [])
    via_moves = plan.get('move_vias', [])
    moved_vias = {s['uuid']: s for s in via_moves}
    obsolete_vias = plan.get('remove_obsolete_vias', [])
    obsolete_ids = {s['uuid'] for s in obsolete_vias}
    check('unique_obsolete_vias', len(obsolete_ids) == len(obsolete_vias)
          and not obsolete_ids & (set(deletions) | {s['uuid'] for s in reassignments} | set(moved_vias)))
    reassigned = {s['uuid']:s for s in reassignments}
    check('unique_via_reassignments', len(reassigned) == len(reassignments))
    check('unique_via_moves', len(moved_vias) == len(via_moves)
          and not set(moved_vias) & (set(reassigned) | set(deletions)))
    check('retained_copper_matches_plan',
          {r['uuid'] for r in reg['changed_retained_copper']} == set(reassigned) | set(moved_vias))
    for id_, spec in reassigned.items():
        p, q = a.by_id.get(id_), b.by_id.get(id_)
        ok = isinstance(p, pcb.PCB_VIA) and isinstance(q, pcb.PCB_VIA)
        if ok:
            ok &= via_snapshot(a.board, p) == spec['source_expected']
            ok &= spec['net'] != p.GetNetname() and 'GND' not in [spec['net'], p.GetNetname()]
            expected = {**spec['source_expected'], 'net': spec['net']}
            if 'position_mm' in spec:
                expected['position_mm'] = spec['position_mm']
            ok &= via_snapshot(b.board, q) == expected
        check('reassigned_via_' + id_, ok)
    for id_, spec in moved_vias.items():
        p, q = a.by_id.get(id_), b.by_id.get(id_)
        ok = isinstance(p, pcb.PCB_VIA) and isinstance(q, pcb.PCB_VIA)
        if ok:
            ok &= via_snapshot(a.board, p) == spec['source_expected'] and p.GetNetname() != 'GND'
            ok &= spec['position_mm'] != spec['source_expected']['position_mm'] and bool(spec.get('reason', '').strip())
            ok &= via_snapshot(b.board, q) == {**spec['source_expected'], 'position_mm': spec['position_mm']}
        check('moved_via_' + id_, ok)
    check('exact_deleted_copper_set', set(reg['removed_copper']) == set(deletions) | obsolete_ids
          and len(deletions) == len(set(deletions)) and set(snapshots) == set(deletions))
    for id_ in deletions:
        old = a.by_id.get(id_)
        expected = snapshots.get(id_)
        ok = old is not None and type(old).__name__ == 'PCB_TRACK' and id_ not in b.by_id
        if ok:
            actual = {'net':old.GetNetname(),'layer':a.board.GetLayerName(old.GetLayer()),
                      'width_mm':old.GetWidth()/1e6,'start_mm':list(xy(old.GetStart())),
                      'end_mm':list(xy(old.GetEnd()))}
            ok &= actual == expected
        check('deleted_track_' + id_, ok)
    for spec in obsolete_vias:
        id_ = spec['uuid']
        old = a.by_id.get(id_)
        ok = isinstance(old, pcb.PCB_VIA) and id_ not in b.by_id
        if ok:
            contacts = via_contact_layers(a.board, old, deletions)
            ok &= old.GetNetname() != 'GND' and via_snapshot(a.board, old) == spec['source_expected']
            ok &= len(contacts) <= 1 and contacts == spec['remaining_contact_layers']
            ok &= bool(spec.get('reason', '').strip())
        check('obsolete_via_removed_' + id_, ok)
    expected_new = set()
    for i, s in enumerate(plan.get('vias', [])):
        id_ = str(uuid.uuid5(uuid.NAMESPACE_URL, plan['revision'] + '/via/' + str(i)))
        expected_new.add(id_); v = b.by_id.get(id_)
        ok = isinstance(v, pcb.PCB_VIA) and list(xy(v.GetPosition())) == s['position_mm'] and v.GetNetname() == s['net']
        if ok:
            ok &= v.GetViaType() == pcb.VIATYPE_THROUGH and abs(v.GetDrillValue()/1e6-s.get('drill_mm',.3)) < 1e-7
            ok &= all(abs(v.GetWidth(lid)/1e6-s.get('diameter_mm',.5)) < 1e-7 for lid in b.ids.values())
        check('new_via_' + id_, ok)
    for i, s in enumerate(plan.get('routes', [])):
        for j, (start,end) in enumerate(zip(s['points_mm'],s['points_mm'][1:])):
            id_ = str(uuid.uuid5(uuid.NAMESPACE_URL, plan['revision'] + '/route/' + str(i) + '/' + str(j)))
            expected_new.add(id_); t = b.by_id.get(id_)
            check('new_track_' + id_, t is not None and not isinstance(t,pcb.PCB_VIA)
                  and all(abs(x-y)<1e-6 for x,y in zip(xy(t.GetStart()),start))
                  and all(abs(x-y)<1e-6 for x,y in zip(xy(t.GetEnd()),end))
                  and t.GetNetname()==s['net'] and b.board.GetLayerName(t.GetLayer())==s['layer']
                  and abs(t.GetWidth()/1e6-s['width_mm'])<1e-7)
    check('exact_new_copper_set', {uid(t) for t in b.tracks}-{uid(t) for t in a.tracks} == expected_new)
    check('exact_moved_pad_set', set(reg['changed_pads']) == moved_pad_ids | activated_pad_ids)
    check('activated_pads_not_moved', not (moved_pad_ids & activated_pad_ids))
    check('exact_moved_guard_set', set(reg['changed_keepouts']) == moved_guard_ids)
    check('exact_moved_footprint_set', set(reg['moved_footprints']) == set(moves))
    def edges(c):
        return sorted((uid(d),d.GetShapeStr(),xy(d.GetStart()),xy(d.GetEnd()),d.GetWidth())
                      for d in c.board.GetDrawings() if c.board.GetLayerName(d.GetLayer())=='Edge.Cuts')
    check('board_outline_unchanged', edges(a) == edges(b))
    check('all_prior_pad_connections', not reg['lost_pad_connections'])
    check('power_width', all(r['status']=='PASS' for r in reg['power_width']))
    check('critical_adjacency', all(r['status']=='PASS' for r in reg['critical_placement']))
    check('unchanged_other_project_members', not reg['changed_project_members'])
    check('retained_reference_copper', not reg['retained_trace_reference_loss'])
    check('new_reference_copper', all(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] <= 1e-6 for r in reg['new_copper_review']))
    flags = {r['uuid'] for r in reg['reference_transitions'] if r['status']=='FAIL'}
    old_flags = {r['uuid'] for r in old_reg['reference_transitions'] if r['status']=='FAIL'}
    check('no_new_transition_flags', flags <= old_flags)
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'checks':checks,
            'source_sha256':a.sha,'candidate_sha256':b.sha,'plan_revision':plan['revision'],
            'strict_audit_status':reg['regression_status'],
            'strict_audit_expected_differences':{'footprints':sorted(moves),'pads':sorted(moved_pad_ids | activated_pad_ids),'guards':sorted(moved_guard_ids),'removed_tracks':sorted(deletions),'removed_obsolete_vias':obsolete_vias,'pth_layer_activations':activation_rows,'reassigned_vias':reassignments,'moved_vias':via_moves,'power_zone_expansions':expansion_rows},
            'pth_reference_review':pth_return_reviews,
            'scope':'Exact planned native differences plus electrical regression; local visual review separate. Not physical or manufacturing qualification.',
            'manufacturing_release':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ['source','candidate','plan','regression','source_regression','output']:
        p.add_argument(name)
    a=p.parse_args();r=review(a.source,a.candidate,a.plan,a.regression,a.source_regression)
    Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'status':r['status'],'errors':r['errors'],'checks':len(r['checks'])}))
