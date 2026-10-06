"""Publish a new independent addendum. Formal board files are read-only."""
from pathlib import Path
import json,hashlib,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];R=HERE/'reports'
NAME='MORI_power_J10_C4_CANDIDATE';D=HERE/NAME;PCB=D/(NAME+'.kicad_pcb')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,j:p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
inv=json.loads((R/'invariants.json').read_text());assert inv['status']=='PASS'
assert sha(PCB)==inv['C4_sha256']==json.loads((R/'FINAL_command.json').read_text())['pcb_sha256']
drc=json.loads((R/'FINAL_drc.json').read_text());assert not any(drc[x]for x in ['violations','unconnected_items','schematic_parity','ignored_checks'])
assert json.loads((R/'FINAL_erc_command.json').read_text())['returncode']==0
assert json.loads((R/'load_path_audit.json').read_text())['status']=='PASS'
visual=json.loads((R/'visual_review_record.json').read_text());assert visual['after_sha256']==sha(PCB)
images=json.loads((R/'visual_sources.json').read_text());assert images['after']==sha(PCB)
formal=json.loads((ROOT/'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json').read_text())
assert all(sha(ROOT/p)==h for p,h in formal.items())
source=json.loads((R/'C3_input_hashes.json').read_text());assert all(sha(ROOT/p)==h for p,h in source.items())
base=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A6_J10_C3.json'
a6=json.loads(base.read_text())
head=ROOT/'hardware/v1_2/head_harness_evidence_20261003'
evidence=json.loads((head/'evidence.json').read_text())
head_manifest=json.loads((head/'delivery_manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in head_manifest['files'].items())
hp=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A7_J10_C4_head_harness.json'
assert not hp.exists(),'Do not overwrite an already-published handoff.'
handoff=dict(revision='V1.2-H0.5-P5R7-PREARRIVAL-A7',date='2026-10-03',
 status='PASS',scope='Candidate routing and documented head-interface evidence delivery only; no manufacturing, physical-fit or complete-harness approval',
 base_handoff=str(base.relative_to(ROOT)),base_handoff_sha256=sha(base),
 candidate=dict(project=str((D/(NAME+'.kicad_pro')).relative_to(ROOT)),pcb=str(PCB.relative_to(ROOT)),pcb_sha256=sha(PCB),
  schematic=str((D/(NAME+'.kicad_sch')).relative_to(ROOT)),schematic_sha256=sha(D/(NAME+'.kicad_sch')),
  outline_mm=[80,55],thickness_mm=1.6,copper_layers=4,placement_source='C3 == C2/A3',
  footprint_count=112,pad_count=280,via_count=147,footprints_pads_vias_nets_outlines_unchanged=True,
  new_mechanical_datums=[],routing_changes=['CHG_N channel','CHG_N board-edge foldback','CHG_N endpoint join','5V_MOTION feedback jog','BAT_ADC Q11/R11 corridor','ARM_Q R54 branch'],
  signal_segment_width_mm=.2,power_widths_changed=False,marking='PCB title/comment and shorter C4 silkscreen updated'),
 J10=a6['J10'],backside_candidates=a6['backside_candidates'],backside_basis=a6['backside_basis'],
 checks=dict(ERC=0,DRC=0,unconnected=0,schematic_parity=0,ignored=0,load_paths=27,load_path_status='PASS',
  formal_files_unchanged=len(formal),C3_unchanged=True,visual_scope=visual['scope'],visual_records=str((R/'visual_review_record.json').relative_to(ROOT)),
  flag_dispositions=visual['dispositions'],body_crossing_candidates_foreign=0,own_escape_dispositions=70,
  model_reference_report=str((R/'model_references.json').relative_to(ROOT))),
 head_harness=dict(report=str((head/'README.md').relative_to(ROOT)),evidence=str((head/'evidence.json').relative_to(ROOT)),evidence_sha256=sha(head/'evidence.json'),
  pinmap=str((head/'head_interface_pinmap_revA.csv').relative_to(ROOT)),
  status='BLOCKED',confirmed_scope='Electrical functions plus exact catalogue candidates, not actual matched parts',
  primary_missing=['OV3660 complete FPC SKU/length/geometry/contact direction','Manufacturer-approved CAM33700 extension, if required','Actual CAM SH/GH header and matched-cable MPN/mated views','SCS0009 p4/p8 pin-numbering view and supplied splitter/tail details','USB source/plug cable SKU and CC topology','Head harness wire OD, bends, anchors, full lengths and dynamic life'],
  mechanical_receipt=evidence['received_mechanical'],formal_pinmap_modified=False),
 report=str((HERE/'README.md').relative_to(ROOT)),review_page=str((HERE/'review.html').relative_to(ROOT)),
 remaining_mechanical_items=a6['remaining_mechanical_items'],formal_boards_replaced=False,PHC1_merged=False,mechanical_main_modified=False,
 physical_tests='NOT_TESTED',procurement_release='BLOCKED',manufacturing_release='BLOCKED')
dump(hp,handoff)
files={str(p.relative_to(ROOT)):sha(p)for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'and '__pycache__'not in str(p)and p.suffix not in ['.kicad_prl','.lck']}
files[str(hp.relative_to(ROOT))]=sha(hp)
dump(HERE/'delivery_manifest.json',dict(date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',scope='Review-delivery integrity only',pcb_sha256=sha(PCB),files=files,head_manifest=str((head/'delivery_manifest.json').relative_to(ROOT)),head_manifest_sha256=sha(head/'delivery_manifest.json'),formal_release=False))
print('Published',str(hp.relative_to(ROOT)),sha(PCB))
