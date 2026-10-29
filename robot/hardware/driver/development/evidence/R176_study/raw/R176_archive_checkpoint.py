"""Freeze native R176 comparisons without adopting any candidate or changing the source."""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
study=dev/'evidence/R176_study';source=dev/'native';board='MORI_Interface_C3.kicad_pcb'
expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
members={x['member']:x['sha256'] for x in read(dev/'evidence/R168G/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
rows=[]
for file in sorted(b.glob('R176?-drc.json')):
 rev=file.name.removesuffix('-drc.json');d=read(file);a=read(b/(rev+'-audit.json'))
 assert read(b/(rev+'-plan.json'))['board_sha256']==expected and sha(b/rev/board)==a['board_sha256']
 row=dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),GND_group_sizes=[len(g) for g in a['GND_groups']],critical_adjacency_passes=sum(x['status']=='PASS' for x in a['critical_placement']),old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],power_failures=[dict(net=x['net'],width_mm=x['width_mm'],lost_pairs=len(x['lost_pairs'])) for x in a['power_width'] if x['status']=='FAIL'],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),adopted=False)
 vf=b/(rev+'-verify/result.json')
 if vf.exists():
  v=read(vf);p=read(b/(rev+'-planned-delta.json'));i=read(b/(rev+'-inspection.json'))
  assert v['erc_violations']==0 and i['source_ground_vias_preserved']==114
  assert all(sha(b/rev/n)==h for n,h in members.items())
  row.update(enabled_ERC=0,planned_delta_checks=len(p['checks']),planned_delta_errors=p['errors'],source_ground_vias_preserved=114,same_face_body_hits=len(i['same_face_nominal_body_hits']),opposite_or_internal_body_hits=len(i['opposite_or_internal_body_hits']))
 rows.append(row)
assert len(rows)>=10
tests=read(b/'R176-guard-checks/result.json');assert len(tests['checks'])==18 and all(x['status']=='PASS' for x in tests['checks'])
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf'])
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/r['revision'] for r in rows]
for top in sorted(b.glob('R176*')):
 for p in ([top] if top.is_file() else sorted(x for x in top.rglob('*') if x.is_file())):
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py','R171E-plan.json','R174-expanded-placement.json','R175_guarded_loops_expanded.py','R175_power_spines.py','R175_r6_pose_screen.py']:
 preserve(b/name,Path('raw/helpers')/name)
for name in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(source/board,Path('source_R168G.kicad_pcb'))
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R176.json'))
viewed=['R176A-B.png','R176G-B.png','R176H-In3.png']
write(study/'visual_review.json',dict(scope='Three actually viewed local native-copper renders; no whole-board or physical qualification.',images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],findings=['A shows the original LIMIT remnants enclosing the U1701 FAULT pad; source port diagnostics confirm no permitted transfer from that local region.','G shows vertical IN- and horizontal IN+ placement with actual LIMIT routing; the IC and passive bodies remain at native size.','H In3 shows the long explicit GND route crossing the 3V3 distribution region; native checks identify a split between 39 and 17 power pads.'],whole_board_visual='NOT_TESTED',thermal_coupling='NOT_TESTED',manufacturer_layout='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=expected,current_source_unchanged=True,candidates=rows,completed_native_trials=len(rows),adopted_revision=None,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,unchanged_canonical_non_PCB_members=77,guard_partition_checks=18,native_guard_roundtrips=4,native_rule_constraints_changed=False,
 key_results=['Repartition now retains a source guard UUID even when a small move vacates its original piece. The native union, fixed via cutouts, flags and all zone identities remain exact; 18 checks and four native roundtrips passed.',
 'A-C retain two same-face input resistors and replace obsolete local leads. C has 25 opens/1 dangling and no new reference gap; source supply/ground/LIMIT are incomplete.',
 'Removing old LIMIT remnants opens a bounded FAULT proposal, but E native validation cuts CAM_BAT_OUT, HEAD_VM and WHEEL_VM. Do not reuse the 42.46 mm proposal as an accepted route.',
 'A 0.25 mm R1707 shift hits C1601 courtyard. Horizontal R1706 at (44.5,14.6) hits U1701 courtyard/silkscreen. Native pose screening finds seven B-face R1706 positions; (44.75,15)/0 is built in G onward.',
 'H restores inputs, LIMIT, all 155 GND pads and local supply/sample branches: 21 opens/0 other DRC/0 parity/0 enabled ERC. Its 25.593 mm total new GND copper is an unqualified long return, and it splits the existing MOTION_3V3 distribution into 39/17 pad groups.',
 'H planned delta has 2561 checks; old connectivity and power fail. C has 2581 checks with the same failure classes. Passing adjacency and reference checks does not make either candidate acceptable.',
 'I reconnects old pad groups but has a non-centered endpoint, 3 new reference deficits and a 0.2 mm power-width failure. J shifts the transfer: native DRC is zero, but J701.1 UPS_5V becomes disconnected, two original UPS reference areas regress, and power remains failed. Both rejected.',
 'The corrected distribution planner protects candidate GND trace reference copper too. K uses an 11.732 mm, 0.30 mm In2 repair without another supply via. Native K restores 3V3 pad connectivity but cuts UPS_5V, ACT_BAT_SWITCHED and HEAD_VM; 23 opens/0 other DRC and no new reference deficit do not permit adoption.',
 'The initial groundguard wrapper applied its replacement before the nested source existed, making no change. Its duplicate result is preserved as a rejected helper experiment. The corrected allrefs wrapper asserts exactly one late replacement before its actual search.'],
 known_search_record_limit='When the last task is ALREADY_NATIVE_CONNECTED, the scratch loop file does not flush that last skip row. G act_sample is confirmed separately in its native audit; no missing row is treated as a passed test.',
 board_enlargement_necessity='NOT_PROVEN',local_space_limit='CONFIRMED_FOR_DOCUMENTED_FIXED_NEIGHBOUR_POSES',bounded_searches_are_not_global_no_fit=True,
 next_actions=['Continue from exact R168G source plans, with H as an unadopted explicit-loop comparison only.',
 'Use full source power connectivity/width requirements, not just the four local 0.48 mm planning spines. Protect GND trace reference copper against new signal-via antipads as well.',
 'Avoid repeating I/J manual coordinate guesses. Jointly screen the 3V3 repair, shorter RLIMIT return, FAULT escape and neighbouring power copper; native pad/keepout/courtyard geometry is decisive.',
 'If broader component movement is necessary, include the neighbouring C1601/power branch group in a concrete static comparison. Preserve fixed mechanical interfaces; board/fixed-interface changes require confirmation.',
 'Retain the short input/LIMIT restoration evidence, but do not adopt a long analog return or degraded old supplies to reduce opens.'],
 manufacturer_layout='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=len(rows),all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=expected,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R176',latest_study_evidence='evidence/R176_study/summary.json',latest_study_adopted=False,latest_study_note='R176 records native original-face and pin-ordered group comparisons. H restores explicit local loops but has 21 opens and a split 3V3 distribution; later repairs remain subject to all power/reference checks. Long RLIMIT return remains unqualified. No candidate adopted; R168G remains at 20 opens.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(payloads=len(payloads),native_trials=len(rows),canonical_unchanged=True,remaining=20)))
