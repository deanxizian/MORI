"""Preserve R166 native trials and endpoint evidence without adopting a PCB."""
import collections,gzip,hashlib,json,math,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R166_study';board='MORI_Interface_C3.kicad_pcb'
old='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
assert not study.exists() and sha(source/board)==old
status=read(dev/'STATUS.json');assert status['revision']=='C3 R165M' and status['unconnected_items']==21
source_files={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
members={r['member']:r['sha256'] for r in read(dev/'evidence/R165M/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(source/name)==digest
trials=[]
for rev,expected in [('R166A',(21,0)),('R166B',(27,0)),('R166C',(24,11)),('R166D',(24,3)),('R166E',(24,3))]:
 d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));i=read(b/(rev+'-inspection.json'));p=read(b/(rev+'-plan.json'))
 assert p['board_sha256']==old and (len(d['unconnected_items']),len(d['violations']))==expected
 assert not d['schematic_parity'] and i['source_ground_vias_preserved']==114
 trials.append(dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=True,adopted=False,unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=0,DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),power_width_failures=[dict(net=r['net'],width_mm=r['width_mm'],lost_pairs=len(r['lost_pairs'])) for r in a['power_width'] if r['status']!='PASS'],old_connection_losses=[r['net'] for r in a['lost_pad_connections']],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),source_ground_vias_preserved=114,planned_new_trace_length_mm=sum(math.dist(x,z) for r in p['routes'] for x,z in zip(r['points_mm'],r['points_mm'][1:])),enabled_ERC='NOT_RERUN_FOR_REJECTED_TRIAL'))
for rev in ['R166D','R166E']:
 for suffix in ['Q-recovery-search','other-fault-search']:
  rows=read(b/(rev+'-'+suffix)/'searches.json')['results']
  assert all(r['result']['status']=='NO_RASTER_CONNECTION' for r in rows if r['request'].startswith('fault'))
 diagnosis=read(b/(rev+'-fault-endpoint-diagnostics.json'))
 assert all(r['via_free_points']==0 for r in diagnosis['reachable_layers'])
 assert all(r['raster_points']==0 for r in diagnosis['reachable_layers'] if r['layer']!='B.Cu')
study.mkdir();payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel;compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/rev for rev in ['R166A','R166B','R166C','R166D','R166E']]
for top in sorted(b.glob('R166*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['R138_joint_search.py','R151_power_region_bridge.py','R151_power_region_bridge_v2.py','R152_render_highlight.py','R153_run_trial.py','R161_power_aware_search.py','R161R_inspection.py','R162_inspection.py','R162_power_spine.py']:
 preserve(b/name,Path('raw/helpers')/name)
for name in ['build_trial.py','copper_geometry.py','audit_candidate.py','footprint_side_change.py','zone_expansion.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R166.json'))
(study/'source_R165M.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
assert gzip.decompress((study/'source_R165M.kicad_pcb.gz').read_bytes())==(source/board).read_bytes()
viewed=[b/'R166A-views'/n for n in ['In2.Cu.png','In3.Cu.png','B.Cu.png']]+[b/'R166D-views'/n for n in ['candidate_B.png','candidate_F.png','source_B.png']]
write(study/'visual_review.json',dict(scope='Six native geometry views actually inspected; no candidate accepted. This is a diagnostic review, not complete layout or physical qualification.',images_actually_viewed=[dict(path='raw/'+p.relative_to(b).as_posix(),source_sha256=sha(p)) for p in viewed],findings=['A shows the new long In2 FAULT path; filled-copper regression identifies the severed 3V3 connection.','D/source B comparison shows Q1701 rotated and moved with its original input leads removed; the input restoration is incomplete.','The F view confirms U1702 is on the opposite face. C through-via collision is established by native DRC; a B-face-only placement screen cannot qualify a through hole.'],local_status='INCOMPLETE',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',adopted=False))
v2=read(b/'R166-placement-screen-v2.json');native_pins=v2['native_Q1701_pins']
assert next(r['net'] for r in native_pins if r['pad']=='Q1701.2')=='/17 {slash} Actuator_Overcurrent/ACT_UV_N'
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),remote_main='aa94dddebcc8ca40cc4b63616147f81448ef087f',source_revision='C3 R165M',source_sha256=old,current_source_unchanged=True,adopted_revision=None,candidates=trials,remaining_unconnected_items=21,baseline_unconnected_items=40,remaining_connectivity_fraction=.525,connectivity_fraction_is_not_engineering_progress=True,progress=[
 'The completed current-board screen covers 17 nets and 26 group pairs. Twenty-five pairs have no raster connection; one FAULT search initially exhausted 250000 states.',
 'Extending that same search to 314168 expanded states produced the A proposal. A connects Q1701 FAULT but splits MOTION_3V3; all five tested widths fail. It is rejected despite zero ordinary DRC violations.',
 'The source 0.48mm In2 supply corridor between (60.725,13.525) and (68.25,12.7) was extracted and reserved. B routes around it but breaks five existing supply networks. It is rejected; no new width or clearance exemption is introduced.',
 'No 0.50mm power bridge proposal was found on A without new vias, with 0.80/0.30mm vias or with 0.60/0.30mm vias under the retained foreign-fill/reference/body constraints. These are bounded searches, not global impossibility results.',
 'The first pose screen omitted courtyard overlap. Native C exposed overlap with U402 as well as a proposed FAULT via short to F-face U1702.3 and native keepout violations. The second screen reproduces the exact C courtyard rejection and retains only 12 combined poses.',
 'D and E keep C1702 fixed and move Q1701 (+0.25,-0.25)mm at 90 or 270 degrees. Both preserve all 50 power widths and old references, but their original ENABLE and ACT_UV_N links are not restored. Each has 24 opens and three dangling warnings; neither is accepted.',
 'Independent no-new-via proposals were found for three original input links in each D/E pose. They have not been combined, snapped, built or accepted. FAULT searches against all three other groups fail under these fixed geometries.',
 'Endpoint diagnostics show B-only reachable regions of 4.255mm2 (D) and 5.5075mm2 (E), with no legal through-via grid points. D is constrained by D1801 front guards/pads and reference retention; E by front U1702 guards/pads and reference retention.'
 ],native_Q1701_pins=native_pins,pin_readback_correction='Q1701.2 is ACT_UV_N, not GND. U1702 is F-face TPS3700DDCR at (57.5,15.75), angle 180; C1702 is B-face 100nF at (59.5,13.2), angle 90. These native values supersede an incorrect conversation recap; no source net was changed.',next_actions=[
 'Continue from canonical R165M, not any R166 trial. Jointly compare U1702, Q1701 and its original supply/return/input-output routes to open a legal bottom escape; include native courtyards, both-face pads, all keepouts, original reference coverage and the 0.48mm power corridor.',
 'Retain the current C1702 supply-bypass screening and all original protection, pin assignments and 114 GND vias. Use the actual U1702 F-face native geometry before constructing any new through hole.',
 'If a feasible grouped pose is found, rebuild all original ENABLE/ACT_UV_N links plus the new FAULT link in a complete explicit plan; native DRC, source connectivity, all power widths, reference and local layer review must pass before adoption.',
 'The 21 remaining connections, full-board style, manufacturer/power/protection/coupling review, BOM/pin map, mechanical/harness handoff and physical qualification remain open.'
 ],source_ground_vias_preserved=114,unchanged_canonical_non_PCB_members=77,whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,unchanged_native_members_omitted=omitted,source_non_PCB_members=members,source_board='source_R165M.kicad_pcb.gz',original_local_sources_preserved=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_files=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_trials=5,all_original_byte_hashes_match=True,canonical_source_unchanged=True,canonical_sha256=old,source_members_unchanged=77,original_local_trials_untouched=True,adopted=False))
status.update(last_followup_study='R166',latest_study_evidence='evidence/R166_study/summary.json',latest_study_adopted=False,latest_study_note='R166 A-E are not adopted. A/B break source power, C fails native placement/through-via checks, D/E preserve power but leave original links open and have no reachable legal FAULT via in the fixed geometry. Continue jointly with actual F-face U1702 and Q1701; canonical R165M remains 21 opens / 52.5 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(archived_payloads=len(payloads),native_trials=5,source_unchanged=True,adopted=False,remaining_unconnected_items=21)))
