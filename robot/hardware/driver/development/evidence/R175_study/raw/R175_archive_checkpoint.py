"""Freeze R175 supply reservations, native comparisons and bounded failures.

No candidate is adopted. Preserve accepted R168G, the original 77 non-PCB
members, all original local trials and previous evidence. Offline evidence
does not establish manufacturer, physical or manufacturing qualification.
"""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';study=dev/'evidence/R175_study';board='MORI_Interface_C3.kicad_pcb'
expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
members={x['member']:x['sha256'] for x in read(dev/'evidence/R168G/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
rows=[]
for letter in 'ABCDEFGHI':
 rev='R175'+letter;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
 assert read(b/(rev+'-plan.json'))['board_sha256']==expected and a['board_sha256']==sha(b/rev/board)
 assert not d['schematic_parity']
 row=dict(revision=rev,board_sha256=a['board_sha256'],native_completed=True,adopted=False,
  unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=0,
  DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
  ground_pad_group_sizes=[len(g) for g in a['GND_groups']],
  critical_adjacency_passes=sum(r['status']=='PASS' for r in a['critical_placement']),
  old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
  power_failures=[dict(net=r['net'],width_mm=r['width_mm'],lost_pairs=len(r['lost_pairs'])) for r in a['power_width'] if r['status']=='FAIL'],
  old_reference_losses=len(a['retained_trace_reference_loss']),
  new_reference_gaps=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),
  enabled_ERC='NOT_RERUN_FOR_REJECTED_TRIAL')
 if letter in 'AG':
  v=read(b/(rev+'-verify/result.json'));p=read(b/(rev+'-planned-delta.json'));i=read(b/(rev+'-inspection.json'))
  assert (v['unconnected_items'],v['violations'],v['erc_violations'])==(31,7,0)
  assert p['errors']==['all_prior_pad_connections','power_width']
  assert i['source_ground_vias_preserved']==114 and not i['same_face_nominal_body_hits']
  assert all(sha(b/rev/n)==h for n,h in members.items())
  row.update(enabled_ERC=0,planned_delta_checks=len(p['checks']),planned_delta_errors=p['errors'],
   source_ground_vias_preserved=114,new_same_face_body_hits=0,
   opposite_or_internal_body_hits=len(i['opposite_or_internal_body_hits']))
 rows.append(row)
assert rows[6]['ground_pad_group_sizes']==[155]
for ix in [0,6]:
 a=read(b/(rows[ix]['revision']+'-audit.json'))
 assert all(r['status']=='PASS' for r in a['power_width'] if (r['net']=='/UPS_BAT' and r['width_mm']==.48) or (r['net']=='MOTION_3V3' and r['width_mm'] in [.3,.4,.48]))
 assert rows[ix]['old_reference_losses']==rows[ix]['new_reference_gaps']==0
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf'])
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R175'+x) for x in 'ABCDEFGHI']
tops=sorted(set(b.glob('R175*'))|set(b.glob('R174B-R175-*')))
for top in tops:
 for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:
   omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py','R174_restore_loops.py','R174D-plan.json']:
 preserve(b/name,Path('raw/helpers')/name)
for name in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R175.json'))
preserve(source/board,Path('source_R168G.kicad_pcb'))
viewed=['R175A-B.png','R175A-F.png','R175G-B.png']
write(study/'visual_review.json',dict(scope='Three actually viewed native-copper local renders; not whole-board review or physical qualification.',
 images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],
 findings=['A keeps the rotated INA300 pose and changes the input transfer and explicit inner ground return. Native power and reference checks confirm restoration of the prior UPS/3V3 wide-copper regressions.',
 'A front view shows the input resistor between neighbouring sample/sense routing and other-layer body/pad restrictions. Its bounded outward-access region has no legal transfer in the tested search.',
 'G rotates the supervisor to 180 degrees and C1304 to 0 degrees. All 155 GND pads form one native group, with an explicit approximately 3.677 mm B-face capacitor-to-supervisor GND trace. Its CT pin and supply/input branches are still unfinished.',
 'Small local route bends still need complete-loop style review. The new same-face nominal body-hit count is zero for A/G; opposite/internal projections and manufacturer, thermal and coupling requirements are not qualified.'],
 whole_board_visual='NOT_TESTED',manufacturer_layout='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_revision='C3 R168G',source_sha256=expected,current_source_unchanged=True,completed_native_trials=9,candidates=rows,
 adopted_revision=None,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,
 connectivity_fraction_is_not_engineering_progress=True,unchanged_canonical_non_PCB_members=77,
 supply_reservations=dict(reference_revision='R174B unadopted native placement',width_mm=.48,
  corridors=['UPS central and right on In2.Cu','MOTION_3V3 upper and lower on In3.Cu'],
  full_strokes_covered_by_native_copper=True,first_UPS_bounded_search='No path in rectangle y>=4; expanded to cover native copper at y<4, then found a reservation.',
  does_not_validate_current_capacity=True),
 key_results=['A replaces the IN- via with (46.35,10.325) and routes the In3 GND return around the native 3V3 corridor. UPS_BAT 0.48 and MOTION_3V3 0.30/0.40/0.48 native checks restore. Both old and new reference checks have no additional deficit.',
  'A and G pass the exact planned geometry checks; only prior pad connectivity and source power branches remain failed. Their 31 opens and 7 dangling items are not acceptable replacements for R168G.',
  'G restores all 155 GND pads after rotating U1302 180 degrees and C1304 0 degrees; explicit GND/VS/SENSE routes are built. CT is not restored. R1310 placement search within a 4 mm exploratory bound found no fixed-neighbour proposal.',
  'H rotates U1302 to 270 degrees at the same centre, but introduces six pad/via or hole-clearance errors and one courtyard overlap. Reject it; do not infer exact pad positions from rotation intuition.',
  'The R1706 bounded pose screen found 11 F-face candidates and no B-face candidate with all neighbours fixed. A second native position still has no tested INA+ route.',
  'D/F explicitly retire five adjacent old front sampling/stub segments; I additionally retires the long old INA+ horizontal segment and raises R1701 0.5 mm. Sequential inputs and branch restoration are still incomplete. The widened I search still finds no INA+ path; these diagnostic deletions cannot be adopted.'],
 bounded_searches_are_not_global_no_fit=True,board_enlargement_necessity='NOT_PROVEN',
 corrected_scratch_helper_errors=['Missing box import in initial pose helper, corrected before its completed screen.','Nested-wrapper quoting in ground-only helper, corrected before its completed screen.','Wide-search loader matched both an embedded string and final exec; restricted replacement to the final complete line before execution.'],
 next_actions=['Keep R168G as the actual source. Rebuild from its exact plan, never treat a rejected candidate as accepted.',
  'Retain R175 actual supply reservations and native restoration evidence. Do not reuse the old R174 bad IN- transfer or old ground cut through 3V3.',
  'Compare complete group poses with actual endpoint escape and transfer access in addition to adjacency. The current 270-degree INA300 pose still traps IN+ in the tested bounded cases; moving just R1706/R1701 or deleting only the sampled neighbours was insufficient.',
  'The 180-degree supervisor/capacitor pair restores GND but still needs the CT resistor and power/enable/armed paths solved together. Do not accept the 13.9 mm ground proposal from C; G has the shorter explicit loop.',
  'Use native pad/net coordinates; H shows that guessed rotational pin coordinates are unreliable. Search exact pose/ports before another native build.',
  'Restore ACT/WHEEL/3V3 branches and U1702 INA+ before evaluating any FAULT progress. Do not rerun identical fixed-layout searches.',
  'Keep reporting local space limits promptly. If an actual board/fixed-interface change is proposed, prepare its native model and static comparison before adoption approval.'],
 manufacturer_layout='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
 assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=9,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=expected,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R175',latest_study_evidence='evidence/R175_study/summary.json',latest_study_adopted=False,
 latest_study_note='R175 restores the R174 UPS/3V3 wide-copper failures with native supply reservations. A/G have 31 opens, 7 dangling and no new reference deficit. G restores all 155 GND pads, but CT/input/source branches remain incomplete. Nine native comparisons remain unadopted; R168G stays at 20 opens.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(payloads=len(payloads),native_trials=9,canonical_unchanged=True,remaining=20)))
