"""Freeze R170 rejected native comparisons without changing the accepted source."""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R170_study';board='MORI_Interface_C3.kicad_pcb';old='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==old
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
members={r['member']:r['sha256'] for r in read(dev/'evidence/R168G/adoption.json')['member_checks']};assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
assert read(b/'R170-source-retention.json')['status']=='PASS'
trials=[]
for suffix,expected in zip('ABCDEFGHIJ',[(25,8),(25,8),(25,8),(25,9),(26,12),(25,10),(25,9),(35,13),(34,13),(28,8)]):
 rev='R170'+suffix;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));p=read(b/(rev+'-plan.json'));assert p['board_sha256']==old and (len(d['unconnected_items']),len(d['violations']))==expected and not d['schematic_parity']
 trials.append(dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=True,adopted=False,unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=0,DRC_types=dict(collections.Counter(v['type'] for v in d['violations'])),lost_old_connection_nets=[v['net'] for v in a['lost_pad_connections']],power_width_failures=[dict(net=v['net'],width_mm=v['width_mm'],lost_pairs=len(v['lost_pairs'])) for v in a['power_width'] if v['status']!='PASS'],ground_pad_group_sizes=[len(g) for g in a['GND_groups']],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(v['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for v in a['new_copper_review']),enabled_ERC=0 if suffix in 'HJ' else 'NOT_RERUN_FOR_REJECTED_TRIAL'))
last=read(b/'R170J-verification/result.json');assert last['unconnected_items']==28 and last['ina300_rlimit_return_screen']=='FAIL' and last['erc_violations']==0
review=read(b/'R170J-planned-delta.json');assert review['status']=='FAIL'
inspection=read(b/'R170J-inspection.json');assert inspection['source_ground_vias_preserved']==114 and not inspection['same_face_nominal_body_hits']
assert all(sha(b/'R170J'/n)==h for n,h in members.items())
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R170'+r) for r in 'ABCDEFGHIJ']
for top in sorted(b.glob('R170*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for n in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py']:
 preserve(b/n,Path('raw/helpers')/n)
for n in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/n,Path('raw/helpers')/n)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R170.json'));preserve(source/board,Path('source_R168G.kicad_pcb'))
viewed=['R170D-B.png','R170E-In3.png','R170-source-In3.png','R170H-B.png','R170H-F.png','R170J-B.png']
write(study/'visual_review.json',dict(scope='Six actually viewed local native-geometry diagnostics; not full-board or physical qualification.',images_actually_viewed=[dict(path='raw/'+n,source_sha256=sha(b/n)) for n in viewed],findings=['D shows the original INA300 orientation, left-side RLIMIT, restored LIMIT and retired WHEEL feed. Its GND fill reconnects the resistor, but no explicit RLIMIT return is present.','E and the unchanged source In3 views show the new long GND return cutting the 3V3 distribution. Exact native audits establish the split; E is not acceptable despite explicit-return PASS.','H B/F views show four passives rearranged with INA300 half-turned and R1706 on the front. The local C1701 VS/GND leads are routed; input, LIMIT, feed and RLIMIT return restoration remains incomplete.','J B shows the 1.8 mm IN- connection and retained feed tracks. The old 3V3 via and B lead still violate the rotated INA300 native keepout. The new-segment body screen does not waive this retained-segment violation.'],new_same_face_nominal_hits=0,new_opposite_internal_overlap_count=7,local_status='FAIL',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=old,current_source_unchanged=True,adopted_revision=None,candidates=trials,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,exact_source_vias_preserved=325,original_R108P_GND_vias_preserved=114,unchanged_canonical_non_PCB_members=77,final_planned_review=dict(status=review['status'],checks=len(review['checks']),errors=review['errors']),progress=[
 'Original-orientation FAULT port diagnosis identifies four retained crossing segments across S2, D1001-K and WHEEL_TX. They are not redundant; retirement produces three S2 groups and opens the other original nets.',
 'A tests FAULT via (43.6,7.4) and creates one small retained 5V-reference loss. B moves the port to (43.6,7.55), removing that loss while retaining all 50 power-width checks. LIMIT and the original crossing links still require restoration.',
 'Joint R1701/R1707 screening yields 37 geometric pairs. C moves RLIMIT to B (42.75,9.875)/270 degrees and restores LIMIT and a WHEEL B detour; that detour isolates the RLIMIT GND pad. D leaves WHEEL explicitly open and restores 155-pad GND plane connectivity, without a direct resistor-to-IC return.',
 'E adds a B/In3 explicit return via an existing GND via and passes the necessary return-path screen, but splits 3V3; WHEEL and original signals are still open. F removes the failed In3 segment. G corrects the remaining B endpoint to native (39.9214,6.4064); (39.95,6.4) was only a raster terminal, not the via centre. No source GND via moved.',
 'Independent searches on F put the proposed WHEEL and GND restorations into the same In3 corridor and cut power. They were not combined or accepted. Original B FAULT trunk proposal is also a long multi-via detour; it is not adopted.',
 'Half-turn four-passive screens first produce no joint result. Extending the prospective replacement set to five non-GND transfers and obsolete right-side GND leads, plus a 0.125 mm grid and resistor side comparison, yields a bounded 500-layout beam. The return-scored pass includes distance to actual U1701.8; it is still placement evidence only.',
 'H uses U1701 B (47.25,12.35)/180, R1701 B (47.375,9.75)/0, C1701 B (43.25,12.125)/270, R1707 B (51.25,11)/270 and R1706 F (47,8.875)/270. R1310 remains the R169D comparison at F (51.25,14.25)/0. Short C1701 VS/GND leads are present; every original via remains at its original pose.',
 'I restores IN- using a 1.8 mm horizontal B trace. J restores seven original tracks retired only for prospective via movement; 5V and UPS original power checks recover. J is 28 opens / 8 other / 0 parity / 0 enabled ERC, all 155 GND pads connected and no new/retained reference loss. ACT_BAT_SWITCHED, WHEEL_VM and 3V3 still fail connectivity, explicit RLIMIT return fails, and the old 3V3 via plus B lead violate the rotated native guard.',
 'TI SBOS613C page 3 was rechecked live: pin 4 ENABLE, pin 8 GND, pin 9 VS. Existing pin mapping and numerical project gates remain unchanged; complete manufacturer layout qualification is not established.',
 'All ten completed native comparisons, scripts, bounded searches, raw failures and six viewed images are frozen. The accepted source and 77 non-PCB members remain unchanged; no manufacturing, deployment, PR merge or physical action occurred.'
],next_actions=[
 'Keep R168G as the accepted source. J is an explicit comparison plan, not a new baseline; neither its IN- restoration nor any candidate connection counts reduce the accepted 20 opens.',
 'For the half-turn layout, jointly relocate the original 3V3 transfer at (46.3,11.85) and its B/F leads, with C1701 supply and the actual VS/ENABLE pins. Preserve all native body restrictions and old power-width/reference checks. J retains the illegal feed to expose the complete function that must be replaced, not to exempt it.',
 'Restore IN+, LIMIT, R1701 direct GND return, R1706/R1707 power taps, ENABLE, R1310 CT/power and FAULT trunk together. H fixed-layout searches provide only the short IN- path; IN+, LIMIT and source-to-bypass power searches have no raster connection. Change relevant placement/transfers before repeating searches.',
 'Original-orientation port B remains a comparison option only if all four crossed old segments, LIMIT, WHEEL and explicit RLIMIT return can be restored without the E power split or long unreviewed detours.',
 'Complete whole-board routing/style, six accepted historical reference-transition flags, manufacturer/power/protection/BOM/pin reviews, mechanical/harness integration and physical qualification before claiming the full objective complete.'
],whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary);write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==old and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=10,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=old,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R170',latest_study_evidence='evidence/R170_study/summary.json',latest_study_adopted=False,latest_study_note='R170 A-J are not adopted. Original-orientation outlet and half-turn four-passive layouts were compared. J restores IN- and retained feeds but leaves original functions, direct RLIMIT return and a 3V3 keepout conflict unresolved. Canonical R168G remains 20 opens / 50 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(payloads=len(payloads),native_trials=10,canonical_unchanged=True,remaining=20)))
