"""Freeze R177 native comparisons and verified supply reservations; adopt none."""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
study=dev/'evidence/R177_study';source=dev/'native';board='MORI_Interface_C3.kicad_pcb'
expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
members={x['member']:x['sha256'] for x in read(dev/'evidence/R168G/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
rows=[]
for suffix in 'ABCDEFGHIJK':
 rev='R177'+suffix;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
 assert read(b/(rev+'-plan.json'))['board_sha256']==expected and sha(b/rev/board)==a['board_sha256']
 row=dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),GND_group_sizes=[len(g) for g in a['GND_groups']],critical_adjacency_passes=sum(x['status']=='PASS' for x in a['critical_placement']),old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],power_failures=[dict(net=x['net'],width_mm=x['width_mm'],lost_pairs=len(x['lost_pairs'])) for x in a['power_width'] if x['status']=='FAIL'],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),adopted=False)
 vf=b/(rev+'-final-checks/result.json')
 if vf.exists():
  v=read(vf);p=read(b/(rev+'-planned-delta.json'));i=read(b/(rev+'-inspection.json'))
  assert v['erc_violations']==0 and i['source_ground_vias_preserved']==114 and p['status']=='PASS'
  assert all(sha(b/rev/n)==h for n,h in members.items())
  row.update(enabled_ERC=0,planned_delta_checks=len(p['checks']),planned_delta_status=p['status'],source_ground_vias_preserved=114,same_face_body_hits=len(i['same_face_nominal_body_hits']),opposite_or_internal_body_hits=len(i['opposite_or_internal_body_hits']))
 else:row['enabled_ERC']='NOT_RERUN'
 rows.append(row)
assert len(rows)==11
reservations=read(b/'R177-supply-reservations-v3/result.json')
assert reservations['source_sha256']==expected and len(reservations['roundtrip_checks'])==50 and all(x['status']=='PASS' for x in reservations['roundtrip_checks'])
tests=read(b/'R177-supply-reservation-tests.json')
assert [len(x['failures']) for x in tests['results']]==[2,0,5]
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf'])
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/r['revision'] for r in rows]
for top in sorted(b.glob('R177*')):
 for p in ([top] if top.is_file() else sorted(x for x in top.rglob('*') if x.is_file())):
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py']:
 preserve(b/name,Path('raw/helpers')/name)
for name in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(source/board,Path('source_R168G.kicad_pcb'))
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R177.json'))
viewed=['R177A-B.png','R177G-views/B.Cu.png','R177G-views/F.Cu.png','R177G-views/In1.Cu.png','R177G-views/In4.Cu.png','R177G-views/source-B.Cu.png','R177K-views/B.Cu.png','R177K-views/In3.Cu.png']
write(study/'visual_review.json',dict(scope='Eight actually viewed native local plots; no whole-board or physical qualification.',images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],findings=[
 'A exposes the rotated diode port; its small local move still has no guarded FAULT route.',
 'G provides deliberate B-face CLR and FAULT paths without new vias. No same-face nominal body crossing; new CLR crosses the actual opposite L701/SW projection. Both intervening GND layers cover the new CLR stroke, but this is not magnetic/noise-margin/thermal qualification.',
 'Source CLR already has a smaller L701/SW projection. The G concern is an increase, not a claim that every opposite-face overlap is forbidden.',
 'K places D302 near the left header and adds one short FAULT transfer. Its B CLR line cuts the lower J102.2 thermal connections: native R25 counts 2 instead of 4. Do not waive the rule.',
 'K diode Fab also projects 1.167462 mm2 into MOUNT_H1 regions. Preserve their native faces/flags; actual mounting/tail clearance is not established by PCB DRC.'
 ],whole_board_visual='NOT_TESTED',thermal_coupling='NOT_QUALIFIED',manufacturer_layout='NOT_QUALIFIED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=expected,current_source_unchanged=True,candidates=rows,completed_native_trials=11,adopted_revision=None,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,unchanged_canonical_non_PCB_members=77,native_rule_constraints_changed=False,
 supply_reservations=dict(checked_power_nets=10,checked_widths_mm=[0,.2,.3,.4,.48],roundtrip_checks_passed=50,serialized_zone_reservations=11,conservative_native_component_fallbacks=7,whole_board_copper_capacity_claim=False,positive_and_negative_tests='raw/R177-supply-reservation-tests.json'),
 key_results=[
 'Replace four local spines with source-pair-checked reservations for all ten power nets. Path trees remain inside original copper; seven regions conservatively retain native components. All 50 checks pass after WKB serialization/reconstruction.',
 'Initial exact shared-boundary subtraction loses two width checks after recombination; the failure is reproduced. V3 keeps a 1 um overlap only at added-zone joins, with negligible area difference, and does not weaken the unchanged checker. Removing required 3V3 reservations fails all five widths as a negative control.',
 'Current D302 CLR leads differ from historical R128G. Five exact current tracks are explicitly replaced; old R128 coordinates were not reused blindly.',
 'A/B use the small 90-degree move. B restores CLR and returns to 20/0/0, but the guarded FAULT link remains unavailable in that fixed layout.',
 'Native footprint/pad/track/courtyard and reachable-space screening compares 580 local poses. Leftward C/D have real silk overlaps. F at B (20.25,7.5)/270 is clear; G combines both signal routes.',
 'G is 19 opens/0 other DRC/0 parity/0 enabled ERC; 2516 planned checks, all old connections, 50 power widths, 155 GND pads, 63 adjacencies, old/new reference and 114 source GND vias pass. It is NOT adopted: local design review of the increased CLR-under-L701/SW projection remains open.',
 'G new CLR has continuous In1/In4 GND projection. TI TPS54302 page 21 does not impose an all-layer CLR/inductor ban; the avoidance experiment is a planning choice, not a changed native requirement. Source CLR already overlaps a smaller portion of this region.',
 'With L701 projection avoided, the small window has no joint optimistic pose. Wider native screening yields 3924 placement candidates and 278 optimistic two-net poses with silk-shape clearance; these counts do not prove actual routes or global infeasibility.',
 'H is rejected for a PTH inside courtyard and silk/mask overlap. I is rejected for silk/mask overlap and has no FAULT route. Additional explicit PTH/land and exposed-copper silk screens select J at B (5.5,2.75)/270.',
 'K connects both nets outside L701 and preserves all 50 power/reference checks, but native R25 J102.2 thermal count is 2 rather than 4. Its 2514 planned checks pass; native DRC still fails. K is not adoptable.',
 'Protecting a 1 mm PTH-ground neighbourhood is overconservative. A second search uses actual native 0.254 mm thermal gaps, 0.30 mm B-zone clearance and 0.05 mm additional planning margin. FAULT has the same proposal; CLR still has no fixed-layout raster route. No native rule or threshold changed.'
 ],
 board_enlargement_necessity='NOT_PROVEN',local_space_limit='CONFIRMED_FOR_DOCUMENTED_FIXED_NEIGHBOUR_POSES',bounded_searches_are_not_global_no_fit=True,
 next_actions=[
 'Continue from exact R168G. G and K remain independent comparisons, never accepted baselines.',
 'Resolve G local coupling/thermal review from actual switch copper, ground layers, diode/CLR function and inductor data; do not infer a blanket opposite-face ban from projection alone.',
 'If pursuing the L701-avoidance route, jointly adjust relevant movable components/old leads and actual J102.2 thermal geometry. Keep all four connections and review the H1 mounting and connector-tail envelope; do not repeat the unchanged J position search.',
 'Use the 50-check supply reservations for new proposals; regenerate them when physical power objects change. Source-width preservation and native R25 are separate requirements.',
 'Keep the remaining INA300, other 18 nets and full engineering review in scope; D302 reaching 19 opens in an unadopted candidate does not reduce the accepted count.',
 'If fixed board/connector changes become necessary, prepare exact native alternatives and static comparisons for user confirmation. Current finite searches do not establish that need.'
 ],manufacturer_layout='NOT_QUALIFIED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=11,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=expected,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R177',latest_study_evidence='evidence/R177_study/summary.json',latest_study_adopted=False,latest_study_note='R177 verifies reservations against all 50 source power-width checks and builds eleven D302 comparisons. G reaches 19/0/0/0 but its increased CLR/inductor/SW projection review remains open; K avoids L701 but fails native R25 at J102.2. Neither adopted; R168G remains at 20 opens.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(payloads=len(payloads),native_trials=11,canonical_unchanged=True,remaining=20)))
