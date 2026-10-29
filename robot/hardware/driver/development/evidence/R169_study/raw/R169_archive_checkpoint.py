"""Freeze rejected R169 INA300 escape comparisons without changing canonical PCB."""
import collections,gzip,hashlib,json,math,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R169_study';board='MORI_Interface_C3.kicad_pcb';old='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==old
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
source_files={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
members={r['member']:r['sha256'] for r in read(dev/'evidence/R168G/adoption.json')['member_checks']};assert len(members)==77
assert all(sha(source/n)==h for n,h in members.items())
trials=[]
for rev,expected in [('R169B',(24,3)),('R169C',(21,0)),('R169D',(26,5)),('R169E',(24,3))]:
 d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));p=read(b/(rev+'-plan.json'))
 assert p['board_sha256']==old and (len(d['unconnected_items']),len(d['violations']))==expected and not d['schematic_parity']
 trials.append(dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=True,adopted=False,unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=0,DRC_types=dict(collections.Counter(v['type'] for v in d['violations'])),lost_old_connection_nets=[v['net'] for v in a['lost_pad_connections']],power_width_failures=[dict(net=v['net'],width_mm=v['width_mm'],lost_pairs=len(v['lost_pairs'])) for v in a['power_width'] if v['status']!='PASS'],ground_pad_group_sizes=[len(g) for g in a['GND_groups']],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(v['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for v in a['new_copper_review']),enabled_ERC=0 if rev=='R169E' else 'NOT_RERUN_FOR_REJECTED_TRIAL'))
checks=read(b/'R169-guard-repartition-checks.json');assert checks['status']=='PASS' and len(checks['checks'])==12
prior=read(b/'R169-R168G-review-regression-v2.json');assert prior['status']=='PASS' and len(prior['checks'])==2566
screen=read(b/'R169-R1310-pose-screen.json');assert len(screen['poses'])==12 and sum(bool(x['legal_port_grid_points']) for x in screen['poses'])==10
last=read(b/'R169E-verification/result.json');assert last['ina300_rlimit_return_screen']=='FAIL' and last['erc_violations']==0
assert all(sha(b/'R169E'/n)==h for n,h in members.items())
inspection=read(b/'R169E-inspection.json');assert inspection['source_ground_vias_preserved']==114 and not inspection['same_face_nominal_body_hits']
plan=read(b/'R169E-plan.json');trunk=plan['routes'][1];trunk_length=sum(math.dist(a,z) for a,z in zip(trunk['points_mm'],trunk['points_mm'][1:]))
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R169'+r) for r in 'ABCDE']
for top in sorted(b.glob('R169*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for n in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161_power_aware_search.py','R161R_inspection.py','R162_inspection.py','R166_endpoint_diagnostics.py','R167_joint_pose_screen.py']:
 preserve(b/n,Path('raw/helpers')/n)
for n in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/n,Path('raw/helpers')/n)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R169.json'));preserve(source/board,Path('source_R168G.kicad_pcb'))
viewed=[b/'R169B-views'/(l+'.png') for l in ['F.Cu','B.Cu','In4.Cu']]+[b/'R169E-views'/(l+'.png') for l in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']]
write(study/'visual_review.json',dict(scope='Nine actual local native-geometry diagnostic views, not physical photos or full-board qualification.',images_actually_viewed=[dict(path='raw/'+p.relative_to(b).as_posix(),source_sha256=sha(p)) for p in viewed],findings=[
 'B F/B views show the half-turned INA300 FAULT pad on the right, opposite the original R1310 pads and the CT transfer. U1701.8 on the left is electrically isolated; these images are not a completed pin restoration.',
 'B In4 and E In1/In4 views show the unchanged source reference plane structure and the added FAULT-hole clearance. Exact audits, not image dimensions, establish zero retained/new trace-reference loss.',
 'E F view shows R1310 at (51.25,14.25)/0 degrees and the restored CT and 3V3 F leads. E B view shows the short FAULT pad-to-via escape while the input/LIMIT and explicit GND restoration remain incomplete.',
 'E In2 view shows the FAULT diagonal and longer trunk dividing existing power regions. Native filled-copper audits establish 3V3 connectivity/0.20/0.30 mm failures. No pass is inferred from a clear signal path.',
 'E In3 view and all six projections were inspected locally. Twenty new opposite/internal overlaps affect C1002, C1404, J401, R1304, R1306, R404, U1302 and U402; full coupling and thermal review is not performed for this rejected trial.'
],new_same_face_nominal_hits=0,opposite_internal_overlap_count=20,local_status='FAIL',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',adopted=False))
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=old,current_source_unchanged=True,adopted_revision=None,failed_pre_native_build=dict(revision='R169A',native_completed=False,reason='Rotating original fragmented via guards produced disconnected native rule-area outlines; build refused before DRC.'),candidates=trials,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,tool_validation=dict(explicit_guard_repartition_checks=12,unchanged_R168G_plan_checks=2566,all_rules_and_thresholds_unchanged=True),progress=[
 'Five original-orientation FAULT/ADC requests in full-fill avoidance and weighted modes yield ten bounded NO_RASTER_CONNECTION results on canonical R168G. They are not a proof of global unroutability.',
 'The original U1701.5 escape has 29 reachable B raster points and zero through-via ports. Its LIMIT lead, opposite Q1601 drain copper, reference guards and pads constrain the exit.',
 'Explicit guard repartition retains all original zone UUIDs and native settings, the exact rotated body minus unchanged fixed cutouts, and every 114 source GND via. It is opt-in and refuses mixed restrictions or missing reconstruction. Source-derived per-UUID review handles rotationally invariant disabled containers without masking real geometry changes.',
 'B rotates U1701 in place by 180 degrees and removes only declared old IN+/IN-/LIMIT and GND terminal tracks. Native B has 24 opens / 3 other; its FAULT endpoint reaches 616 B raster points but no legal via because of R1310 and the CT region. All original INA300 connections still require restoration.',
 'C keeps the original U1701 orientation and removes only six LIMIT tracks. Native C is 21 opens / 0 other; its endpoint grows to 2684 B raster points but still has no through-via port. This diagnoses opposite Q1601 and reference constraints without accepting removal of LIMIT.',
 'Joint R1310 screening produces 12 native-geometry poses, ten with prospective FAULT ports while every source via remains fixed. D uses R1310 F (51.25,14.25)/0 degrees and FAULT via (49.45,14.0). D is 26 opens / 5 other, including unfinished R1310 and INA300 connections; it is not adopted.',
 'D searches provide CT and R1310 power restorations without foreign-fill cuts and a 17.861017 mm raster FAULT proposal with three potential power-cut regions. E uses exact native endpoints; the actual In2 FAULT trunk is %.9f mm. It joins U1701.5 to the main FAULT group and restores R1310, but splits 3V3 and fails width 0/0.20/0.30 mm screens.' % trunk_length,
 'E is 24 opens / 3 other / 0 parity / 0 enabled ERC. U1701.8 remains isolated (154+1 GND groups), its old IN+/IN-/LIMIT links remain open, and explicit RLIMIT-to-GND return fails. There are no old/new trace-reference losses and no new own-face nominal body hits, but that does not make the candidate acceptable.',
 'The canonical PCB and all 77 non-PCB native source members are unchanged. Nine local comparison views and all original study data are preserved; current accepted connectivity remains 20/40, not E counts.'
],next_actions=[
 'Continue from canonical R168G; no R169 candidate is an adopted baseline. Do not count the E FAULT connection until all original functions and power paths are restored.',
 'For the half-turn route, jointly compare U1701, C1701, R1701, R1706/R1707, R1310 and necessary explicitly identified non-ground transfers. Restore both sense inputs, LIMIT, the actual U1701.8 ground pin and R1701.1 explicit return. The current fixed-cutout rotation also collides with old 3V3 via (46.3,11.85) and its B lead; do not exempt them.',
 'If keeping the new FAULT port, reserve the actual old 3V3 paths before rebuilding its trunk or compare other allowed layers. The E In2 route cuts the distribution; neither zero reference gaps nor the restored R1310 branch resolves that.',
 'Original-orientation LIMIT-only removal has already been screened; do not repeat unchanged searches. Opposite Q1601 copper and nearby power/sense transfers must be part of any new original-orientation comparison.',
 'Full-board route style, six historical reference-transition flags, manufacturer layouts, BOM/pins, mechanical/harness integration and physical qualification remain open.'
],source_ground_vias_preserved=114,unchanged_canonical_non_PCB_members=77,whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary);write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_files=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=4,failed_pre_native_builds=1,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=old,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R169',latest_study_evidence='evidence/R169_study/summary.json',latest_study_adopted=False,latest_study_note='R169 A-E are not adopted. Original and half-turn INA300 exits were compared; joint R1310 movement permits a FAULT port, but E cuts 3V3 and leaves INA300 input/LIMIT/GND restoration incomplete. Canonical R168G remains 20 opens / 50 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(payloads=len(payloads),native_trials=4,pre_native_failure=1,actual_E_fault_trunk_mm=trunk_length,canonical_unchanged=True,remaining=20)))
