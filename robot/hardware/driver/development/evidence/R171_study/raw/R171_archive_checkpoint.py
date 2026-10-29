"""Freeze four rejected R171 native candidates, tool validation and diagnostics.

The accepted R168G and every original local trial are preserved byte for byte.
No candidate is adopted and no manufacturing or physical action is performed.
"""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R171_study';board='MORI_Interface_C3.kicad_pcb';expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
members={r['member']:r['sha256'] for r in read(dev/'evidence/R168G/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
validation=read(b/'R171-tool-validation/result.json');native_review=read(b/'R171-native-review/result.json');isolated=read(b/'R171-isolated-contact-checks.json')
assert all(x['status']=='PASS' for x in [validation,native_review,isolated])
trials=[]
for rev,counts in [('R171B',(29,8)),('R171C',(29,7)),('R171D',(28,7)),('R171E',(27,5))]:
 d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));p=read(b/(rev+'-plan.json'))
 assert p['board_sha256']==expected and (len(d['unconnected_items']),len(d['violations']))==counts and not d['schematic_parity']
 trials.append(dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=True,adopted=False,unconnected_items=counts[0],other_DRC=counts[1],schematic_parity=0,DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),ground_pad_group_sizes=[len(g) for g in a['GND_groups']],old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],strict_power_failures=[dict(net=x['net'],width_mm=x['width_mm'],lost_pairs=len(x['lost_pairs'])) for x in a['power_width'] if x['status']=='FAIL'],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),enabled_ERC=0 if rev in ['R171D','R171E'] else 'NOT_RERUN_FOR_REJECTED_TRIAL'))
last=read(b/'R171E-verify/result.json');review=read(b/'R171-native-review/R171E-planned-delta.json');inspection=read(b/'R171E-inspection.json');ina=read(b/'R171E-verify/ina300-return.json')
assert last['unconnected_items']==27 and last['violations']==5 and last['erc_violations']==0 and last['ina300_rlimit_return_screen']=='NOT_TESTED'
assert not ina['rlimit_return']['explicit_track_pad_via_path_without_fills']
assert review['errors']==['all_prior_pad_connections','power_width'] and len(review['checks'])==2598
assert inspection['source_ground_vias_preserved']==114 and not inspection['same_face_nominal_body_hits']
assert all(sha(b/'R171E'/n)==h for n,h in members.items())
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/rev for rev in ['R171B','R171C','R171D','R171E']]
roots += [p.parent for p in (b/'R171-tool-validation').glob('*/'+board)]
for top in sorted(b.glob('R171*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for n in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py']:
 preserve(b/n,Path('raw/helpers')/n)
for n in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/n,Path('raw/helpers')/n)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R171.json'));preserve(source/board,Path('source_R168G.kicad_pcb'))
viewed=['R171D-B.Cu.png','R171D-F.Cu.png','R171D-In3.Cu.png','R171E-B.Cu.png','R171E-F.Cu.png']
write(study/'visual_review.json',dict(scope='Five actually viewed local native-copper diagnostic renders, not screenshots or complete layout qualification.',images_actually_viewed=[dict(path='raw/R171-images/'+n,sha256=sha(b/'R171-images'/n)) for n in viewed],findings=[
 'D B shows the left C1701 VS feed reaching the unchanged upper 3V3 via. Its small terminal joins are still candidate routing, requiring final simplification/review with the completed local circuit.',
 'D F and In3 expose the retained power and transfer topology. The retired transfer at (46.3,11.85) is absent; native audits, not visual inference, establish the actual retained-anchor and reference results.',
 'E B shows ENABLE escaping rightward to the unchanged 3V3 via at (52.45,11.875). E F confirms the replaced upper VS stub is removed. R1310 power and CT remain open.',
 'Both candidate resistor and IC grounds have same-face filled connectivity but no explicit RLIMIT-to-U1701.8 track/pad/via path. This has not passed the required return review.',
 'New mounted-face nominal body intersections are zero. Nine opposite/internal projection hits remain limited evidence, without complete thermal/coupling/manufacturer review.'
],new_same_face_nominal_hits=0,new_opposite_internal_hits=9,local_status='FAIL',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=expected,current_source_unchanged=True,adopted_revision=None,candidates=trials,pre_native_failure=dict(revision='R171A',reason='Preparation rejected two native plane contacts; no plan or completed candidate PCB. The subsequent missing-plan build failure is preserved.'),remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,source_via_retention=native_review['via_checks'],original_R108P_GND_vias_preserved=114,unchanged_canonical_non_PCB_members=77,final_planned_review=dict(status=review['status'],checks=len(review['checks']),errors=review['errors'],power_width_review=review['power_width_review']),final_return_screen=dict(status=last['ina300_rlimit_return_screen'],explicit_path=False,same_face_fill=ina['rlimit_return']['same_mounted_face_filled_component']),tool_validation=dict(helper_cases=len(isolated['checks']),native_build_refusals=4,accepted_R168G_unchanged_checks=2566,invalid_distributed_layer_plan_refused=True),progress=[
 'The old non-ground VS via at (46.3,11.85) contacts In2 and In3 after its replaced F/B leads are omitted. Native source geometry identifies In2 as an isolated approximately 0.201579 mm2 fill island touching no other retained copper; In3 is the real distribution network.',
 'Explicit opt-in permits only proven isolated In2/In3 fill contacts to be discounted when screening an obsolete non-ground transfer. GND vias, real distribution, malformed declarations, missing rationale and snapshot mismatches remain refused. Native refill and full connectivity/width/reference checks remain mandatory.',
 'The strict audit retains every original pair loss. The separate planned review accounts only for pairs involving an exactly verified, removed obsolete via; every retained anchor pair at all original widths remains mandatory. Invalid removal evidence receives no exclusions. R171E still fails ACT_BAT_SWITCHED, WHEEL_VM and MOTION_3V3 connectivity.',
 'B removes the offending via/leads and proposes VS supply, but has a resistor/R1001 courtyard overlap, one isolated GND pad and three reference deficits. C moves R1701 to B (49,9.65)/180 and omits the failed supply path; all 155 GND pads reconnect through fills, but explicit return remains absent.',
 'C supply search has no route on 0.025 mm local raster, but finds a bounded 0.01 mm B-face proposal. D extends it to native existing copper and exact via centre; native refill shows 28 opens/7 dangling, with no new or old reference loss. No rule or clearance was changed.',
 'D local restoration search finds a B ENABLE proposal using no new vias and avoiding foreign power fills. LIMIT, IN+ and explicit GND have no bounded connection in the recorded window with either fill-preserving or ordinary native geometry; this is not a global impossibility proof.',
 'E replaces the original dangling ENABLE lead, extends the proposal to the exact via at (52.45,11.875), and retires the obsolete F VS stub. E is 27 opens/5 dangling/0 parity/0 enabled ERC. Old power connections, other local functions and explicit RLIMIT return remain incomplete, so it is not adopted.',
 'All four completed candidates preserve 324 of 325 original via snapshots exactly, removing only the explicitly reviewed non-ground VS via and adding one FAULT via. All 114 original GND vias are unchanged. Accepted R168G remains untouched.'
],next_actions=[
 'Keep R168G as the accepted source. R171E is an unadopted plan rebuilt from that source, not a qualified new baseline. Its candidate counts do not change the accepted 20/40 remaining.',
 'The half-turn alternative still requires joint placement/transfer reconsideration for IN+, LIMIT and a compact explicit R1701-to-U1701.8 return, plus the R1706/R1707 power taps. Do not repeat the unchanged D bounded searches as new evidence.',
 'Restore R1310 CT/power and original S2, BAT-tap and WHEEL_TX connections, then connect FAULT without cutting the original 3V3 widths. The existing ENABLE/VS candidate routes must be checked again after any group changes.',
 'Preserve native keepouts, all ground vias, fixed interfaces, In2 net allowlist and original width/reference thresholds. Complete local route cleanup, whole-board/manufacturer/power/BOM/pin review and physical qualification before claiming the goal complete.'
],whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary);write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=4,pre_native_failures=1,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=expected,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R171',latest_study_evidence='evidence/R171_study/summary.json',latest_study_adopted=False,latest_study_note='R171 B-E are not adopted. The obsolete VS transfer was explicitly screened, VS and ENABLE were restored in E, but original connections and explicit RLIMIT return remain incomplete. R168G remains 20 opens / 50 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(payloads=len(payloads),native_trials=4,canonical_unchanged=True,remaining=20)))
