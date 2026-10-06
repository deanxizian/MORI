"""Publish an additive C2 study handoff; never publish/replace formal artwork.

Run once after validate_candidate.py. It preserves the received A2 and
adds clearly blocked study metadata to hardware-owned shared contracts.
"""
from pathlib import Path
import collections
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REL = HERE.relative_to(ROOT).as_posix()
OUT = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json'


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(p):
    return sha_bytes(p.read_bytes())


def read(p):
    return json.loads(p.read_text())


def dump(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')


def run():
    assert not OUT.exists(), 'Do not overwrite a received handoff. Use a new addendum.'
    validation = read(HERE / 'validation.json')
    assert validation['integrity_status'] == 'PASS'
    assert validation['reports']['unconnected_items'] == 26
    assert all(sha(ROOT / p) == h for p, h in validation['hashes'].items())
    a2p = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json'
    a2 = read(a2p)
    assert sha(a2p) == 'b7ee51734472dd4a4cab364447354422f3af690250e0d9349caa64c2842945b9'
    assert all(sha(ROOT / p) == h for p, h in a2['native_source_manifest'].items())
    received = []
    for n in ['REVIEW.md', 'review.json']:
        p = ROOT / 'mechanical/studies/prearrival_finish/J10_C2_review' / n
        data = p.read_bytes()
        out = HERE / 'received_mechanical_C2' / n
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(data)
        received.append(dict(source=p.relative_to(ROOT).as_posix(),
                             immutable_copy=out.relative_to(ROOT).as_posix(), sha256=sha_bytes(data)))
    sources = []
    evidence = [
        ('jst_ph_finished_holes', 'https://www.jst.com/resources/faq/', HERE/'jst_faq.html',
         'Material-specific finished plated-hole dimensions; accessed 2026-10-02.'),
        ('jst_ph_catalogue', 'https://www.jst-mfg.com/product/pdf/eng/ePH.pdf', HERE.parent/'sources/jst_ph.pdf',
         'Header/housing nominal dimensions; exact assembled wire-centre Z not closed.'),
        ('jst_handling', 'https://www.jst-mfg.com/product/pdf/eng/handling_e.pdf', HERE.parent/'sources/jst_handling.pdf',
         'Handling/slack guidance; no evidence that project5mm straight allocation is a vendor minimum.'),
        ('B540C', 'https://www.diodes.com/datasheet/download/B540C.pdf', HERE/'B540C.pdf',
         'DS13012 Rev18-2 p4, maximum package including terminals6.22x8.13x2.50mm.'),
        ('JST_PHR8_CAD_request', 'https://www.jst-mfg.com/product/index.php?doc=2&filename=PHR-8.zip&series=199&type=10',
         HERE/'JST_PHR8_CAD_request.html', 'Public request form only; no form submitted or CAD acquired.'),
    ]
    for ident, url, p, note in evidence:
        assert p.is_file()
        sources.append(dict(id=ident, url=url, access_date='2026-10-02', path=p.relative_to(ROOT).as_posix(),
                            sha256=sha(p), note=note))
    for number in ['6711', '6712']:
        source = ROOT / ('mechanical/studies/prearrival_finish/harness_A2/Alpha_'+number+'_official.html')
        data = source.read_bytes()
        p = HERE / ('Alpha_'+number+'_official.html')
        p.write_bytes(data)
        sources.append(dict(id='alpha_'+number, url='https://www.alphawire.com/products/wire/ecogen/ecowire/'+number,
                            access_date='2026-10-02', path=p.relative_to(ROOT).as_posix(), sha256=sha(p),
                            received_from=source.relative_to(ROOT).as_posix(),
                            note='Official HTML received read-only from mechanical. Candidate only; domestic price/stock not confirmed.'))
    sources.append(dict(id='littelfuse_451_453', access_date='2026-10-02',
        url='https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1',
        retrieval='Official PDF read through web tool; direct curl403, no local PDF claimed.',
        document_revision='GD. 12/01/25', page=4,
        package_nominal_mm=[6.10, 2.69, 2.69], plus_tolerance_mm=[.20, .25, .25],
        proposed_additional_assembly_height_mm=.15))
    dump(HERE/'sources.json', sources)
    holes = read(HERE/'PH_finished_hole_audit.json')
    back = read(HERE/'backside_screen.json')
    snap = read(HERE/'candidate_snapshot.json')
    blocker = dict(id='PH_PTH_GLASS_EPOXY_FINISHED_HOLE_20261002', status='FAIL',
        scope='JST B*B-PH-K-S / S*B-PH-K-S on plated glass-epoxy PCB',
        audit=REL+'/PH_finished_hole_audit.json', table=REL+'/PH_finished_hole_audit.csv',
        source='https://www.jst.com/resources/faq/', affected_connectors=len(holes['rows']),
        per_board=dict(collections.Counter(r['board'] for r in holes['rows'])),
        current_nominal_mm=.75, finished_two_pin_range_mm=[.80, .85],
        finished_three_to_sixteen_pin_range_mm=[.85, .90],
        formal_artwork_changed=False,
        required_action='Correct finished holes, lands, tolerance, adjacent tracks and DRC before fabrication. C2 only changes J10; no automatic waiver for other PH connectors.')
    handoff = dict(revision=a2['revision'], addendum_id='P5R7-prearrival-A3-J10-C2', date='2026-10-02',
        status='BLOCKED', scope='Independent placement/interface candidate for review, NOT a published replacement PCB.',
        base_handoff='hardware/v1_2/handoff/mechanical_P5R7.json',
        previous_addendum=a2p.relative_to(ROOT).as_posix(), previous_addendum_sha256=sha(a2p),
        native_source_manifest=a2['native_source_manifest'], native_boards_replaced=False, mechanical_main_modified=False,
        candidate=dict(project=REL+'/MORI_power_J10_C2_CANDIDATE/MORI_power_J10_C2_CANDIDATE.kicad_pro',
                       board=REL+'/MORI_power_J10_C2_CANDIDATE/MORI_power_J10_C2_CANDIDATE.kicad_pcb',
                       hashes=validation['hashes'], status='BLOCKED', affected_nets_unrouted=True,
                       checks=validation['reports'], changes=validation['changed_footprints']),
        J10=dict(part='JST S8B-PH-K-S(LF)(SN)', housing='PHR-8', contact='SPH-002T-P0.5S',
                 pads=snap['footprints']['J10']['pads'], mating_direction_native_xy=[-1,0],
                 numbered_centres_and_nets_unchanged=True, candidate_finished_hole_mm=.90, land_mm=1.50,
                 proposed_finished_hole_tolerance_mm=[-.05,0], fabricator_tolerance_confirmed=False,
                 wire_exit_z_above_board_mm=None, body_bounds_board_mm=[[38.25,25.05,0],[45.85,42.95,4.8]],
                 moving_plug_bounds_board_mm=[[36.25,25.1,0],[43.10,42.9,4.8]],
                 trial_unplug_stroke_mm=5.35, trial_lift_mm=12,
                 stroke_basis='Geometric whole-housing separation plus0.5mm allocation, NOT manufacturer extraction/force specification.'),
        backside_candidates=back['backside_envelopes'], backside_basis=back['bounds_basis'],
        mechanical_received_review=received,
        mechanical_review_scope='Only D30/F70 local envelope clearance and continuous plug-box sweeps. Does not accept the complete PCB, wires, service grip, JP70/R50/TP71 or thermal design.',
        local_extra_vertical_clearance_lower_bound_mm={'D30':1.84,'F70':1.40},
        global_backside_allocation_changed=False,
        wire_study=dict(reference='Alpha5853 AWG26', alternative='Alpha6711 AWG26',
                        alternative_selected=False, baseline_straight_exit_allocation_mm=5,
                        comparison_straight_allocations_mm=[1.5,3,5], allocations_are_vendor_minima=False,
                        alternative_max_od_mm=1.016, alternative_static_radius_mm=5.08,
                        extra_0p3mm_clearance_in_hardware_scan=False,
                        result=REL+'/ecowire_comparison.json', status='NOT_TESTED',
                        full_harness_and_cable_attached_service='BLOCKED', price_and_domestic_cut_length='BLOCKED'),
        formal_board_PH_hole_blocker=blocker,
        pending=['PHR8 mated crimp/wire centre Z, complete contact release and wire-root handling data',
                 'Selected crimped cable OD/bend data/domestic quote',
                 'Full wire/bundle and hand/tool service geometry, candidate JP70/R50/TP71 acceptance',
                 'Finish affected routing, backside return/thermal review and outward-escape review',
                 'Repair all formal PH holes/pads and run complete ERC/DRC before new board handoff'],
        report=REL+'/README.md', evidence_index=REL+'/sources.json',
        physical_tests='NOT_TESTED', procurement_release=False, manufacturing_release=False)
    dump(OUT, handoff)
    # Only additive, hardware-owned metadata. Preserve unrelated fields and A2.
    meta = dict(id=handoff['addendum_id'], date=handoff['date'], status='BLOCKED',
                handoff=OUT.relative_to(ROOT).as_posix(), handoff_sha256=sha(OUT),
                report=REL+'/README.md', candidate_is_published_board=False,
                native_boards_replaced=False, candidate_DRC='FAIL;26 unconnected items;14 warnings',
                physical_tests='NOT_TESTED', manufacturing_release=False)
    backups = HERE/'shared_contracts_before_A3';backups.mkdir(exist_ok=True)
    updates = []
    for name in ['components.json', 'electrical_interfaces.json']:
        p = ROOT/'contracts'/name
        data = p.read_bytes();d = json.loads(data)
        assert 'prearrival_A3_J10' not in d
        (backups/name).write_bytes(data)
        d['prearrival_A3_J10'] = meta
        d['PH_finished_hole_audit_20261002'] = blocker
        if name == 'electrical_interfaces.json':
            d.setdefault('mechanical_handoff_addenda', []).append(OUT.relative_to(ROOT).as_posix())
        assert p.read_bytes() == data, 'Concurrent contract change; stop rather than overwrite.'
        dump(p,d)
        updates.append(dict(path=p.relative_to(ROOT).as_posix(), before_sha256=sha_bytes(data), after_sha256=sha(p)))
    dump(HERE/'A3_publication.json',dict(handoff=OUT.relative_to(ROOT).as_posix(),sha256=sha(OUT),
        shared_contract_updates=updates, formal_sources_unchanged=all(sha(ROOT/p)==h for p,h in a2['native_source_manifest'].items()),
        A2_unchanged=sha(a2p)==handoff['previous_addendum_sha256']))
    print(OUT)
    print('CANDIDATE ONLY / DRC FAIL / NO MANUFACTURING RELEASE')


if __name__ == '__main__':
    run()
