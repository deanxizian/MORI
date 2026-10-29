"""Compare a filled candidate to an immutable native baseline.

This is a design regression check. It does not replace native DRC, visual review,
datasheet review or any physical qualification. Input files are never saved.
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from copper_geometry import *


def audit(before, after, evidence):
    a, b = Copper(before), Copper(after)
    # R17 is the project's explicit inner-zone clearance. Do not assume every
    # transfer is a 0.50-mm via: retained 0.80-mm vias have larger native voids.
    internal_clearance = inner_zone_clearance(after)
    rows = []
    for old in json.loads((evidence / 'power_width_regression.json').read_text())['reports']:
        net = old['net']
        for w in [0, .2, .3, .4, .48]:
            src, dst = a.connected_pairs(net, w), b.connected_pairs(net, w)
            lost = sorted(src - dst)
            rows.append({'net': net, 'width_mm': w, 'source_pairs': len(src),
                         'lost_pairs': lost, 'status': 'FAIL' if lost else 'PASS'})
    connected = []
    for net in sorted({p.GetNetname() for p in a.pads if p.GetNetname()}):
        # Preserve every existing pad/pad connection, not just a shortest ratsnest.
        ids = {uid(p) for p in a.pads if p.GetNetname() == net}
        src = {pair for pair in a.connected_pairs(net) if all(x in ids for x in pair)}
        lost = sorted(src - b.connected_pairs(net))
        if lost:
            connected.append({'net': net, 'lost_pad_pairs': lost})
    # No new ground deficit under retained full copper strokes. Existing deficits
    # remain visible and are not cleared by this delta check.
    refrows = []
    lost_ground_by_layer = {ref: a.copper.get(('GND', ref), GeometryCollection()).difference(
        b.copper.get(('GND', ref), GeometryCollection())) for ref in ['In1.Cu', 'In4.Cu']}
    for t in b.segments:
        layer = b.board.GetLayerName(t.GetLayer())
        if layer not in REFERENCE or t.GetNetname() == 'GND':
            continue
        id_ = uid(t)
        if id_ not in a.by_id:
            continue
        old = a.shapes.get((id_, layer))
        new = b.shapes.get((id_, layer))
        if old is None or new is None or not old.equals_exact(new, 1e-8):
            continue  # Moved/new traces require independent full reference review.
        ref = REFERENCE[layer]
        extra = new.intersection(lost_ground_by_layer[ref]).area
        if extra > 1e-6:
            refrows.append({'uuid': id_, 'net': t.GetNetname(), 'layer': layer,
                            'new_unreferenced_area_mm2': extra})
    oldfps = {f.GetReference(): f for f in a.footprints}
    changed_retained_copper = []
    removed_copper = []
    for old in a.tracks:
        id_ = uid(old)
        new = b.by_id.get(id_)
        if new is None:
            removed_copper.append(id_)
            continue
        different = old.GetNetname() != new.GetNetname() or type(old) != type(new)
        if isinstance(old, pcb.PCB_VIA) and isinstance(new, pcb.PCB_VIA):
            different |= xy(old.GetPosition()) != xy(new.GetPosition()) or old.GetDrillValue() != new.GetDrillValue()
        elif not isinstance(old, pcb.PCB_VIA) and not isinstance(new, pcb.PCB_VIA):
            different |= xy(old.GetStart()) != xy(new.GetStart()) or xy(old.GetEnd()) != xy(new.GetEnd()) or old.GetWidth() != new.GetWidth()
        for layer in LAYERS:
            sa = a.shapes.get((id_, layer), GeometryCollection())
            sb = b.shapes.get((id_, layer), GeometryCollection())
            different |= sa.symmetric_difference(sb).area > 1e-8
        if different:
            changed_retained_copper.append({'uuid': id_, 'source_net': old.GetNetname(), 'candidate_net': new.GetNetname()})
    moved = []
    for f in b.footprints:
        prev = oldfps.get(f.GetReference())
        if prev is None or xy(f.GetPosition()) != xy(prev.GetPosition()) or f.GetOrientationDegrees() != prev.GetOrientationDegrees() or f.GetLayer() != prev.GetLayer():
            moved.append(f.GetReference())
    # Critical placement limits are inherited explicitly; they are project
    # screening distances, not manufacturer maximums.
    pads = defaultdict(list)
    for p in b.pads:
        pads[b.pad_name(p)].append(p)
    placement = []
    for check in json.loads((evidence / 'critical_placement.json').read_text())['checks']:
        pa, pb = pads[check['a']][0], pads[check['b']][0]
        distance = Point(xy(pa.GetPosition())).distance(Point(xy(pb.GetPosition())))
        same_face = b.pad_faces[uid(pa)] == b.pad_faces[uid(pb)]
        ok = distance <= check['target_max_mm'] + 1e-5 and (not check['same_face_required'] or same_face)
        placement.append({**check, 'distance_mm': distance, 'same_face': same_face, 'status': 'PASS' if ok else 'FAIL'})
    groups = b.pad_groups()
    # Each newly added copper shape is checked as a full stroke. Pads already
    # present at the endpoints are explicitly subtracted from body projection
    # checks; their existing projection is not newly routed copper.
    new_copper = []
    for t in b.segments:
        if uid(t) in a.by_id:
            continue
        layer = b.board.GetLayerName(t.GetLayer()); net=t.GetNetname()
        stroke=b.shapes[(uid(t),layer)]
        own_lands=unary_union([s for (id_,ly),s in b.shapes.items() if ly==layer and isinstance(b.by_id[id_],pcb.PAD) and b.by_id[id_].GetNetname()==net])
        outside_lands=stroke.difference(own_lands)
        ref = REFERENCE[layer]
        zone_clearance = max([internal_clearance] + [z.GetLocalClearance()/1e6 for z in b.zones
                             if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(b.ids[ref])])
        surface_regions = [p for p in parts(b.copper[(net,layer)]) if p.intersects(stroke)]
        transfers, transfer_rows = [], []
        for v in b.vias + b.pads:
            face_land = b.shapes.get((uid(v),layer))
            ref_land = reference_transfer_shape(b,v,ref)
            if (v.GetNetname()!=net or face_land is None or ref_land is None
                    or not any(p.intersects(face_land) for p in surface_regions)):
                continue
            # Exclude only the mandatory local void of a same-net plated transfer
            # joined through this surface copper island. Adjacent route segments
            # may share the escape; unrelated holes/plane splits remain errors.
            transfers.append(ref_land.buffer(zone_clearance + .005))
            row = {'uuid':uid(v),'clearance_mm':zone_clearance,'polygon_tolerance_mm':.005}
            if isinstance(v,pcb.PCB_VIA):
                row['diameter_mm'] = v.GetWidth(b.ids[ref])/1e6
            else:
                row.update(kind='circular_plated_pad',pad=b.pad_name(v),drill_mm=xy(v.GetDrillSize()),
                           reference_annulus_flashed=bool(v.FlashLayer(b.ids[ref])))
            transfer_rows.append(row)
        own_transfers=unary_union(transfers)
        reference_raw=outside_lands.difference(b.copper.get(('GND',ref),GeometryCollection()))
        reference_missing=reference_raw.difference(own_transfers)
        hits=[]
        for k in b.keepouts:
            if k['name'].startswith('BODY_'):
                area=outside_lands.intersection(k['shape']).area
                if area>1e-6:
                    hits.append({'body_rule':k['name'],'body_layers':k['layers'],'outside_existing_pad_mm2':area})
        new_copper.append({'uuid':uid(t),'net':net,'layer':layer,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'width_mm':t.GetWidth()/1e6,
                           'reference_uncovered_mm2_outside_existing_lands_and_own_transfers':reference_missing.area,
                           'reference_uncovered_mm2_before_own_transfer_exclusion':reference_raw.area,
                           'own_transfer_voids':transfer_rows,
                           'body_projections_outside_existing_lands':hits})
    changed_pads=[]
    for p in a.pads:
        id_=uid(p);q=b.by_id.get(id_)
        if q is None or q.GetNetname()!=p.GetNetname() or xy(q.GetPosition())!=xy(p.GetPosition()) or xy(q.GetSize())!=xy(p.GetSize()) or xy(q.GetDrillSize())!=xy(p.GetDrillSize()):
            changed_pads.append(id_);continue
        for layer in LAYERS:
            old=a.shapes.get((id_,layer),GeometryCollection());new=b.shapes.get((id_,layer),GeometryCollection())
            if old.symmetric_difference(new).area>1e-8:
                changed_pads.append(id_);break
    old_keepouts={k['id']:k for k in a.keepouts};changed_keepouts=[]
    for k in b.keepouts:
        old=old_keepouts.get(k['id'])
        if old is None or any(k[key]!=old[key] for key in ['name','layers','tracks','vias']) or k['shape'].symmetric_difference(old['shape']).area>1e-8:
            changed_keepouts.append(k['id'])
    changed_keepouts += list(set(old_keepouts)-{k['id'] for k in b.keepouts})
    unchanged_project_members=[];changed_project_members=[]
    for path in Path(before).parent.rglob('*'):
        if path.is_file() and path.name!='MORI_Interface_C3.kicad_pcb' and path.suffix not in ['.kicad_prl','.lck']:
            relative=path.relative_to(Path(before).parent);other=Path(after).parent/relative
            (unchanged_project_members if other.is_file() and path.read_bytes()==other.read_bytes() else changed_project_members).append(str(relative))
    # Identify the actual reference change at every non-ground via by its copper
    # contacts, rather than assuming a through via uses every layer it crosses.
    ground = b.ground_reference_anchors
    transition_rows = []
    for v in b.vias:
        if v.GetNetname() == 'GND':
            continue
        touched = []
        touched_fills = []
        for layer in REFERENCE:
            land = b.shapes.get((uid(v), layer))
            if land is None:
                continue
            others = [s for (i, ly), s in b.shapes.items() if ly == layer and i != uid(v) and b.by_id[i].GetNetname() == v.GetNetname()]
            if any(land.intersects(s) for s in others):
                touched.append(layer)
            if any(land.intersects(s) for net, ly, s in b.fills if net == v.GetNetname() and ly == layer):
                touched_fills.append(layer)
        refs = sorted({REFERENCE[x] for x in touched})
        nearest = sorted((Point(xy(v.GetPosition())).distance(Point(xy(g.GetPosition()))), uid(g)) for g in ground)
        distance, gid = nearest[0] if nearest else (None, None)
        status = 'NOT_APPLICABLE' if len(refs) <= 1 else ('PASS' if distance is not None and distance <= 2 else 'FAIL')
        transition_rows.append({'uuid': uid(v), 'net': v.GetNetname(), 'position_mm': xy(v.GetPosition()),
                                'touched_layers': touched, 'zone_contact_layers': touched_fills,
                                'reference_layers': refs, 'nearest_ground_mm': distance,
                                'nearest_ground_uuid': gid, 'status': status})
    result = {'baseline_sha256': a.sha, 'board_sha256': b.sha, 'scope': 'Copper regression and project screening only; native DRC and visual/electrical checks separate',
              'power_width': rows, 'lost_pad_connections': connected, 'retained_trace_reference_loss': refrows,
              'moved_footprints': moved, 'critical_placement': placement,
              'changed_retained_copper': changed_retained_copper, 'removed_copper': removed_copper,
              'changed_pads':changed_pads,'changed_keepouts':changed_keepouts,'unchanged_project_members':unchanged_project_members,
              'changed_project_members':changed_project_members,'new_copper_review':new_copper,
              'pad_group_opens': sum(len(g)-1 for g in groups.values()),
              'GND_groups': groups.get('GND'), 'reference_transitions': transition_rows,
              'reference_ground_anchor_count': len(ground),
              'reference_ground_anchor_method': 'Positive-area contact with actual In1/In4 GND zone fill; anchor copper is excluded from plane evidence.',
              'manufacturing_release': False}
    result['method_limits'] = ['The seven-flag historical screen uses track contacts. Power-plane contacts are also reported separately and require power-integrity review.',
        'Own-transfer voids use same-net via lands or circular plated-pad reference copper/barrels joined to the reviewed surface island, explicit R17/native reference-zone clearance and 0.005 mm polygon tolerance. Unflashed PTH inner layers use the actual drill barrel, not the larger external pad. SMD, NPTH, slots, unrelated antipads and plane splits receive no new exemption. Earlier reports remain preserved.',
        'Reconstructed width calculations use outward polygon approximation and geometric erosion. Counts at exact width thresholds differ from the unavailable historical script; all newly computed source pairs must be preserved. This is an additional regression, not a claim of byte-identical restoration of that script.']
    result['regression_status'] = 'FAIL' if connected or refrows or changed_pads or changed_keepouts or changed_retained_copper or removed_copper or changed_project_members or any(r['status']=='FAIL' for r in rows + placement) else 'PASS'
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('baseline'); p.add_argument('candidate'); p.add_argument('output')
    args = p.parse_args()
    evidence = Path(__file__).resolve().parents[2] / 'evidence/R108P'
    r = audit(args.baseline, args.candidate, evidence)
    Path(args.output).write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({'regression': r['regression_status'], 'opens': r['pad_group_opens'],
                      'power_width_losses': sum(x['status']=='FAIL' for x in r['power_width']),
                      'reference_losses': len(r['retained_trace_reference_loss']),
                      'transition_flags': sum(x['status']=='FAIL' for x in r['reference_transitions'])}))
