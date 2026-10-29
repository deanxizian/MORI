"""Preserve the R165 studies and receive M into the independent development entry only."""
import collections,csv,gzip,hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';candidate=b/'R165M';board='MORI_Interface_C3.kicad_pcb'
study=dev/'evidence/R165_study';evidence=dev/'evidence/R165M';backup=Path('robot/.state/c3-completion/baseline_R159H_before_R165M')
old='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0';new='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,data):
 with p.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source/board)==old and sha(candidate/board)==new
result=read(b/'R165M-verification/result.json');reg=read(b/'R165M-verification/regression.json');planned=read(b/'R165M-planned-delta.json');inspection=read(b/'R165M-inspection.json');visual=read(b/'R165M-visual-review.json');metrics=read(b/'R165M-metrics.json');plan=read(b/'R165M-plan.json')
assert tuple(result[k] for k in ['board_sha256','unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps'])==(new,21,0,0,0,0)
assert result['ina300_rlimit_return_screen']=='PASS' and result['historical_transition_flags']==6
assert planned['status']=='PASS' and len(planned['checks'])==2807 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(x) for x in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert inspection['source_ground_vias_preserved']==114 and not inspection['same_face_nominal_body_hits']
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==12 and len(visual['opposite_or_internal_projections'])==16
assert metrics['counts']=={'segments':1366,'vias':324,'footprints':215,'new_segments':137}
assert metrics['preserved_In3_0_48_spine_uncovered_mm2']<1e-6 and metrics['lower_power_via_In2_0_48_pair']
assert metrics['group_count_changes']==[{'net':'Net-(U1301-INB-_{slash}_OV)','before':2,'after':1,'after_groups':[['C1302.1','R1306.1','R1307.2','U1301.4']]}]
members={r['member']:r['sha256'] for r in read(dev/'evidence/R159H/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(source/name)==sha(candidate/name)==digest,name
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
old_status=read(dev/'STATUS.json');assert old_status['board_sha256']==old and old_status['unconnected_items']==22
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();now=datetime.now(timezone.utc).isoformat()
study.mkdir();evidence.mkdir()
for p in (b/'R165M-verification').iterdir():shutil.copy2(p,evidence/p.name)
for src,dest in [('R165M-plan.json','plan.json'),('R165M-planned-delta.json','planned-delta.json'),('R165M-inspection.json','inspection.json'),('R165M-visual-review.json','visual_review.json'),('R165M-metrics.json','metrics.json'),('R165M-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dest)
shutil.copytree(b/'R165M-views',evidence/'images')
(evidence/'source_R159H.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
assert gzip.decompress((evidence/'source_R159H.kicad_pcb.gz').read_bytes())==(source/board).read_bytes()
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for n,r in enumerate(read(evidence/'drc.json')['unconnected_items'],1):w.writerow([n,r['description'],' | '.join(q['description'] for q in r['items'])])
payloads=[];omitted=[];trials=[]
def preserve(p,rel):
 data=p.read_bytes();compressed=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288;dest=study/rel
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compressed})
roots=[p for p in b.glob('R165*') if p.is_dir() and re.fullmatch(r'R165[A-Z]',p.name)]
for top in sorted(b.glob('R165*')):
 if top.name=='R165M-views':continue
 files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
 for p in files:
  owner=next((r for r in roots if p.is_relative_to(r)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append({'local_path':p.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(p)});continue
  preserve(p,Path('raw')/p.relative_to(b))
for name in ['build_trial.py','footprint_side_change.py','review_planned_delta.py','zone_expansion.py','copper_geometry.py','audit_candidate.py','verify_trial.py','audit_ina300_return.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R162_inspection.py','R161R_inspection.py','R161_power_aware_search.py','R162_power_spine.py']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R165.json'))
for s in 'ABCDEFGHIJKLM':
 rev='R165'+s;root=b/rev;drc=b/(rev+'-drc.json');r={'revision':rev,'adopted':rev=='R165M','native_completed':drc.exists()}
 if (root/board).exists():r['board_sha256']=sha(root/board)
 if drc.exists():
  d=read(drc);a=read(b/(rev+'-audit.json'));r.update({**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'DRC_types':dict(collections.Counter(x['type'] for x in d['violations'])),'old_connection_losses':[x['net'] for x in a['lost_pad_connections']],'power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'old_reference_losses':len(a['retained_trace_reference_loss']),'new_reference_gaps':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review'])})
 else:r['failure_phase']={'B':'Route simplification preflight rejected; subsequent build had no plan and no PCB.','E':'Native builder rejected guard reconstruction before saving changes; the preserved PCB is an unchanged source copy.','L':'Exact-centre route preflight rejected reference loss; subsequent build had no plan and no PCB.'}[s]
 trials.append(r)
assert sum(x['native_completed'] for x in trials)==10
assert next(x for x in trials if x['revision']=='R165E')['board_sha256']==old
summary={'recorded_at_utc':now,'source_commit':commit,'source_revision':'R159H','source_sha256':old,'remote_main':'aa94dddebcc8ca40cc4b63616147f81448ef087f','adopted_revision':'R165M','adopted_board_sha256':new,'candidates':trials,'M_full_verification':result,'planned_delta':{'checks':2807,'status':'PASS','errors':[]},
'progress':[
'C corrects the R164 shortened middle-node reference gaps. Earlier upper-left UV approaches failed ground thermal rules; this study uses a new left transfer at (46.3,29.65).',
'G new GND via shorted D901/HEAD_BUCK_IN on B. H removes that via; I moves the UV via down 0.05mm and restores all old reference coverage. R1031 retains its original outward F lead and a continuous filled F path to both unchanged local GND vias.',
'J moves the original OV transfer from (54.4,31.8) to (55.9,33.9), and relocates the proposed FAULT transfer to (54.3,33.9). The original U1501.4-to-C1501.1 B filter connection remains; this frees a referenced In3 corridor between two original 3V3 transfers.',
'K restores UV_N with a 19.844077mm In3 route while preserving all 50 source power widths and the explicit 0.48mm In3 supply corridor. Only the original FAULT connection is then missing.',
'L direct endpoint simplification loses 0.101706mm of centreline reference coverage and is rejected before native construction. M uses a verified via-land terminal join and restores FAULT with an 18.257926mm In3 route.',
'M has 21 unconnected items, zero other native DRC/parity/enabled ERC, all prior pad connections restored and all 2807 planned differences checked. The resolved original net is U1301 OV: C1302.1, R1306.1, R1307.2 and U1301.4 are one group.'
],
'search_limits':['The protected-corridor single-layer search on I found two disconnected regions; this was a fixed-geometry bounded result, resolved by moving the two non-ground transfers in J.','Global weighted search proposed about 48mm with three additional vias; it was not adopted. Native/geometry evidence supports the shorter coupled-layout route.'],
'source_ground_vias_preserved':114,'ground_pads_in_one_group':155,'unchanged_non_PCB_members':77,'remaining_unconnected_items':21,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.525,'connectivity_fraction_is_not_engineering_progress':True,
'images':'../R165M/images; twelve native geometry PNGs actually reviewed.','local_projection_review':'../R165M/visual_review.json','whole_board_visual':'NOT_TESTED','whole_board_route_style':'NOT_TESTED','manufacturer_thermal_coupling_qualification':'NOT_TESTED','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False}
write(study/'summary.json',summary)
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R159H_non_PCB_members':members,'unchanged_native_members_omitted':omitted,'M_images':'../R165M/images','original_local_sources_preserved':True,'reconstruction':'Use R159H non-PCB source members plus each exact archived PCB and metadata overlay. Full native plans rebuild from R159H; B/L never produced a candidate, E contains only a source copy.'})
for r in payloads:
 p=study/r['path'];assert sha(p)==r['sha256'];data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes();assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
for r in visual['images_actually_viewed']:assert sha(evidence/r['path'])==r['sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'completed_native_trials':10,'preflight_or_presave_failures':3,'all_original_byte_hashes_match':True,'source_local_trials_untouched':True,'M_images_hash_verified':12,'source_before_adoption_sha256':old})
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert source_all=={p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for name,digest in source_all.items():
 if name!=board:assert sha(source/name)==digest,name
write(evidence/'adoption.json',{'adopted_at_utc':now,'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,'member_checks':[{'member':n,'sha256':sha(source/n)} for n in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status={**old_status,**result};status.update({'revision':'C3 R165M','previous_candidate':'C3 R159H','previous_candidate_sha256':old,'strict_regression_explanation':'Strict raw geometry audit retains FAIL for 17 planned footprint transforms including two face flips, 93 replaced tracks, four moved non-ground vias, two explicitly reassigned non-ground vias and ten retired obsolete transfers. All 2807 planned/native electrical-reference checks pass without rule or threshold relaxation.',
'planned_delta_review_status':'PASS','planned_delta_check_count':2807,'electrical_regression_status':'PASS','local_visual_review':'PASS','local_visual_review_explanation':'Twelve actual native geometry views; zero new same-face nominal-body hits. Sixteen opposite/inner component groups reviewed with explicit reference/coupling/thermal limits. Full-board style, manufacturer and thermal/EMC qualification remain NOT_TESTED.','new_same_face_nominal_body_projection_groups':0,'segment_count':1366,'via_count':324,'footprint_count':215,'remaining_connectivity_fraction':.525,'remaining_U1301_OV_groups':1,'ina300_rlimit_return_evidence':'evidence/R165M/ina300-return.json','last_followup_study':'R165','latest_study_evidence':'evidence/R165_study/summary.json','latest_study_adopted':True,'latest_study_note':'M is accepted into the independent development entry after restoring original UV, FAULT and bias links and joining the U1301 OV net. 21 opens, 52.5 percent by original unconnected count; not manufacturing or overall engineering progress.','goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':'R165M','unconnected_items':21,'remaining_connectivity_fraction':.525,'planned_checks':2807,'payload_count':len(payloads),'completed_native_trials':10,'unchanged_non_PCB_members':77,'goal_complete':False}))
