"""Publish the independently checked PH candidates as A4, without adoption."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REL=HERE.relative_to(ROOT).as_posix()
OUT=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A4_PH.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def run():
    assert not OUT.exists(),'Received handoffs are immutable. Use a new addendum.'
    validation=load(HERE/'validation.json');assert validation['status']=='PASS'
    formal=load(HERE/'formal_source_hashes.json')
    candidate=load(HERE/'candidate_source_hashes.json')
    assert all(sha(ROOT/p)==h for p,h in formal.items())
    assert all(sha(ROOT/p)==h for p,h in candidate.items())
    a3=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json'
    old=load(a3);changes=load(HERE/'pad_changes.json');proposal=load(HERE/'proposal.json')
    board_rows={}
    for kind,v in validation['boards'].items():
        n=v['board'];prefix=REL+'/candidates/'+n+'/'+n
        board_rows[kind]=dict(project=prefix+'.kicad_pro',board=prefix+'.kicad_pcb',schematic=prefix+'.kicad_sch',
            native_hashes={p:h for p,h in candidate.items()if p.startswith(REL+'/candidates/'+n+'/')and p.endswith(('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru'))},
            pad_changes=changes[kind],numbered_hole_centres_unchanged=True,all_component_poses_unchanged=True,
            board_outline_mounting_holes_unchanged=True,all_tracks_vias_widths_unchanged=True,
            connector_rotations_required=[],component_moves_required=[],route_edits_required=[],
            ERC_violations=0,DRC_violations=0,unconnected_items=0,schematic_parity=0,
            CAD_checks='PASS',physical_tests='NOT_TESTED',native_report_directory=REL+'/reports/'+kind)
    handoff=dict(revision=old['revision'],addendum_id='P5R7-prearrival-A4-PH-C1',date='2026-10-02',
      status='BLOCKED',scope='Independent PH finished-hole correction only; formal boards not replaced.',
      previous_addendum=a3.relative_to(ROOT).as_posix(),previous_addendum_sha256=sha(a3),
      formal_native_source_manifest=old['native_source_manifest'],formal_source_manifest=REL+'/formal_source_hashes.json',
      candidate_source_manifest=REL+'/candidate_source_hashes.json',boards=board_rows,
      total_connectors=18,total_changed_holes=69,CAD_checks='PASS',
      source=proposal['source'],source_html_sha256=proposal['source_sha256'],
      hole_requirements=dict(two_pin_nominal_mm=.85,three_to_sixteen_pin_nominal_mm=.90,
                             two_pin_land_mm=1.45,three_to_sixteen_pin_land_mm=1.50,
                             proposed_finished_hole_tolerance_mm=[-.05,0],drawn_annulus_mm=.30),
      fabrication_tolerance_confirmed=False,component_mechanical_envelopes_changed=False,
      mechanical_interface_moves_required=False,native_boards_replaced=False,mechanical_main_modified=False,
      power_J10='Formal vertical orientation retained here; this does not adopt or complete side-entry C2.',
      unreleased_side_entry_C2='Still BLOCKED:26 unconnected items,14 DRC warnings,unknown actual wire exit height/service fit. Merge PH fix and rerun checks when that candidate is finished.',
      remaining_blocks=['PCB-factory written confirmation of finished-hole window, plating/tool compensation, registration and manufactured annulus',
                        'Matching purchased headers, soldering/insertion/retention physical validation',
                        'Explicit formal revision adoption; complete robot and prior power/charging/emergency-stop/harness gates remain unchanged'],
      report=REL+'/README.md',per_hole_table=REL+'/PH_69_finished_holes_and_neighbours.csv',
      validation=REL+'/validation.json',physical_tests='NOT_TESTED',procurement_release=False,manufacturing_release=False)
    dump(OUT,handoff)
    meta=dict(id=handoff['addendum_id'],date=handoff['date'],status='BLOCKED',CAD_checks='PASS',
      handoff=OUT.relative_to(ROOT).as_posix(),handoff_sha256=sha(OUT),report=REL+'/README.md',
      corrected_connectors_in_candidates=18,corrected_holes_in_candidates=69,
      formal_artwork_changed=False,mechanical_interface_changes_required=False,
      manufacturing_release=False,factory_tolerance_confirmed=False,physical_tests='NOT_TESTED')
    backups=HERE/'shared_contracts_before_A4';backups.mkdir(exist_ok=True);updates=[]
    for name in ['components.json','electrical_interfaces.json']:
        p=ROOT/'contracts'/name;raw=p.read_bytes();d=json.loads(raw)
        assert 'prearrival_A4_PH'not in d
        (backups/name).write_bytes(raw)
        d['prearrival_A4_PH']=meta
        # The original FAIL still describes the unmodified formal artwork.
        d['PH_finished_hole_audit_20261002']['independent_correction_candidate']=meta
        if name=='electrical_interfaces.json':d['mechanical_handoff_addenda'].append(OUT.relative_to(ROOT).as_posix())
        assert p.read_bytes()==raw,'Concurrent contract change detected; do not overwrite.'
        dump(p,d);updates.append(dict(path=p.relative_to(ROOT).as_posix(),before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=sha(p)))
    # Keep diagnostic logs, remove only our two incomplete initialization copies.
    failure_logs=HERE/'reports/build_failures';failure_logs.mkdir(exist_ok=True)
    for n in ['initialization_failure_01','initialization_failure_02']:
        path=HERE/n
        if path.exists():
            shutil.copy2(path/'build.log',failure_logs/(n+'.log'))
            shutil.rmtree(path)
    dump(HERE/'publication.json',dict(handoff=OUT.relative_to(ROOT).as_posix(),handoff_sha256=sha(OUT),
      shared_contract_updates=updates,formal_source_files_unchanged=all(sha(ROOT/p)==h for p,h in formal.items()),
      candidate_files_match_checked_hashes=all(sha(ROOT/p)==h for p,h in candidate.items()),
      previous_A3_unchanged=sha(a3)==handoff['previous_addendum_sha256'],native_boards_replaced=False,
      manufacturing_outputs_exported=False,procurement_ordered=False))
    print(OUT)
    print('CAD checks PASS / factory tolerance BLOCKED / candidate only')


if __name__=='__main__':run()
