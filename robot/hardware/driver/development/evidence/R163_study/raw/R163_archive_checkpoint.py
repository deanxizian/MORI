"""Preserve R163 grouped-divider candidates, native checks and tool controls.
Canonical R159H remains unchanged. No candidate is adopted or manufacturable.
"""
import collections,gzip,hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');src=dev/'native'
board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R163_study'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
expected='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
assert not study.exists() and sha(src/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R159H' and status['unconnected_items']==22
members={r['member']:r['sha256'] for r in read(dev/'evidence/R159H/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(src/n)==h for n,h in members.items())
source_all={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()}
v=read(b/'R163F-verification/result.json');a=read(b/'R163F-verification/regression.json');delta=read(b/'R163F-planned-delta.json')
inspection=read(b/'R163F-inspection.json');tests=read(b/'R163-side-change-tests/result.json')
assert (v['unconnected_items'],v['violations'],v['schematic_parity'],v['erc_violations'])==(23,2,0,0)
assert delta['errors']==['all_prior_pad_connections']
assert len(a['power_width'])==50 and all(r['status']=='PASS' for r in a['power_width'])
assert len(a['GND_groups'])==1 and len(a['GND_groups'][0])==155
assert not a['retained_trace_reference_loss'] and not inspection['same_face_nominal_body_hits']
assert v['new_reference_gaps']==0 and v['historical_transition_flags']==6 and inspection['source_ground_vias_preserved']==114
assert v['ina300_rlimit_return_screen']=='PASS' and len(a['lost_pad_connections'])==2
assert tests['status']=='PASS' and tests['test_count']==9
study.mkdir();payloads=[];omitted=[];trials=[]
def write(p,data):
 with p.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def preserve(p,rel):
 data=p.read_bytes();compress=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288
 dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
roots=[b/('R163'+s) for s in 'ABCDEF']+[b/'R163-side-change-tests/native']
for top in sorted(b.glob('R163*')):
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for q in files:
  omitted_member=False
  for root in roots:
   if q.is_relative_to(root):
    rel=q.relative_to(root).as_posix()
    if rel in members and sha(q)==members[rel]:
     omitted.append({'local_path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});omitted_member=True
    break
  if not omitted_member:preserve(q,Path('raw')/q.relative_to(b))
for rev in ['R163A','R163B','R163C','R163D','R163E','R163F']:
 path=b/rev;entry={'revision':rev,'board_sha256':sha(path/board),'adopted':False}
 if rev=='R163A':
  assert entry['board_sha256']==expected
  entry.update({'build_completed':False,'native_DRC_run':False,'reason':'Shapely scale requires a tuple origin; failed before PCB save. Source copy and exact error log preserved.'})
 else:
  d=read(b/(rev+'-drc.json'));reg=read(b/(rev+'-audit.json'))
  entry.update({'build_completed':True,**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'DRC_types':dict(collections.Counter(r['type'] for r in d['violations'])),
   'power_width_failures':[{'net':r['net'],'width_mm':r['width_mm'],'lost_pair_count':len(r['lost_pairs'])} for r in reg['power_width'] if r['status']!='PASS'],
   'old_reference_losses':len(reg['retained_trace_reference_loss']),
   'new_reference_gaps':sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in reg['new_copper_review']),
   'lost_pad_connection_nets':[r['net'] for r in reg['lost_pad_connections']]})
 trials.append(entry)
for name in ['build_trial.py','footprint_side_change.py','review_planned_delta.py','zone_expansion.py','copper_geometry.py','audit_candidate.py','verify_trial.py','audit_ina300_return.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R162_inspection.py','R161R_inspection.py','R162D-plan.json']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R163.json'))
summary={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_revision':'R159H','source_sha256':expected,'adopted_revision':None,'best_verified_working_layout':'R163F',
 'working_native_result':v,'planned_delta_errors':delta['errors'],'planned_check_count':len(delta['checks']),
 'source_ground_vias_preserved':114,'power_width_checks_preserved':50,'ground_pads_in_one_group':155,
 'same_face_nominal_body_hits':0,'opposite_or_internal_projection_hits':len(inspection['opposite_or_internal_body_hits']),
 'remaining_old_connection_nets':[r['net'] for r in a['lost_pad_connections']],'candidates':trials,
 'tool_controls':{'status':'PASS','test_count':9,'evidence':'raw/R163-side-change-tests/result.json',
  'notes':'Explicit two-pad SMD resistor side opt-in, immutable pins/nets/sizes and separately mapped guard face. Native rounded-pad tessellation is checked at target pose with independent analytic centres, keeping the existing geometry threshold. Legacy R162D replay retains exactly its prior connection failure.'},
 'progress':['Grouped the two head protection divider chains by explicitly moving eight resistors. R1302 changes B to F; R1503 changes F to B. All pad numbers, resistor values and schematic nets are preserved.',
  'Restored the UV input through local F/B copper. R716 rotates 180 degrees for an outward 0.50 mm B connection to J702.1, avoiding the adjacent GND terminal.',
  'R1503 now has its OV node at the bottom, allowing the existing lower OV transfer to move to (58.375,34.25). A short In2 return replaces the former long In3 OV trunk without changing the In2 net allow-list.',
  'Five existing HEAD_VM sense tracks widen from 0.20 to 0.25 mm, with a 0.30 mm lower B escape. This preserves the relocated high-side pad\'s inherited 0.20 mm corridor check; it is not a power-current qualification.',
  'F is 23 opens / 2 dangling / 0 parity / 0 enabled ERC, with all recorded power/reference/ground checks preserved. It still breaks the old UV_N and ENABLE links and is not adopted.'],
 'next_actions':['Continue from the explicit F plan rebuilt from R159H, not from a shorted/failed saved candidate. Restore HEAD_UV_N between the new right transfer (64.2,29.7) and its old output group, plus the relocated R1311/R1312 ENABLE bias branch.',
  'The removed U1501 OV In3 trunk opens the central region. Recompute joint routing on this new geometry; the UV middle-node U-shaped route, native H4 keepout and existing FAULT path remain obstacles. Do not combine independent proposals without native revalidation.',
  'All J702 native via restrictions remain. Tentative local sites (58.35,30.95), (58.35,29.35), (59.15,31.05) and (63.4,32.5) are blocked by existing guards and must not be used. Native source openings cannot be extrapolated to nearby points.',
  'Bias front-face fixed-copper search found no pair. Its bounded result is not proof of impossibility. Preserve the recent R159H UPS sample geometry while considering joint moves or explicit old-copper rerouting.',
  'After restoring old links, rerun the complete native/planned/electrical/INA suite and extend visual/manufacturer/thermal/coupling review beyond the six local views. Continue all 22 canonical remaining connections and all engineering work.'],
 'local_view_evidence':'raw/R163F-local-view-review.json','whole_board_visual':'NOT_TESTED','physical':'NOT_TESTED','manufacturer_thermal_coupling_qualification':'NOT_TESTED',
 'canonical_non_PCB_members_preserved':77,'remaining_unconnected_items_in_adopted_development':22,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,
 'connectivity_fraction_is_not_engineering_progress':True,'engineering_status':'FAIL','manufacturing_release':False,'goal_complete':False}
write(study/'summary.json',summary)
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R159H_non_PCB_members':members,'unchanged_native_members_omitted':omitted,'original_local_sources_preserved':True,
 'reconstruction':'Combine R159H non-PCB source members, archived PCB and any saved trial metadata overlays. Side-test mutants are deliberate negative controls, never candidates.'})
for r in payloads:
 q=study/r['path'];assert sha(q)==r['sha256'];data=gzip.decompress(q.read_bytes()) if r['gzip'] else q.read_bytes()
 assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
assert source_all=={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'completed_native_trials':5,'pre_save_failed_source_copy':1,'native_side_test_controls_preserved':True,
 'all_original_byte_hashes_match':True,'source_native_all_members_unchanged':True,'source_local_trials_untouched':True,'source_board_sha256':expected})
status.update({'last_followup_study':'R163','latest_study_evidence':'evidence/R163_study/summary.json','latest_study_adopted':False,
 'latest_study_note':'R163F groups the two head divider chains, restores UV input and OV return, and preserves all 50 power-width/reference/ground checks. It has 23 opens / 2 dangling items and two old logic links unfinished; not adopted. Canonical R159H / 22 opens / 55 percent unchanged.'})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payloads':len(payloads),'completed_native_trials':5,'best_working_layout':'R163F','planned_checks':len(delta['checks']),'adopted':False,'canonical_remaining':22}))
