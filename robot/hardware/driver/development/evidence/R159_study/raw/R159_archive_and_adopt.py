"""Archive R159 A-H and diagnostic evidence; receive H into the independent development entry."""
import csv,gzip,hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';candidate=b/'R159H';board='MORI_Interface_C3.kicad_pcb'
study=dev/'evidence/R159_study';evidence=dev/'evidence/R159H'
backup=Path('robot/.state/c3-completion/baseline_R156G_before_R159H')
old='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
new='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source/board)==old and sha(candidate/board)==new
result=read(b/'R159H-verified/result.json');reg=read(b/'R159H-verified/regression.json')
planned=read(b/'R159H-verified/planned-delta.json');inspect=read(b/'R159H-inspection.json');visual=read(b/'R159H-visual-review.json')
assert (result['board_sha256'],result['unconnected_items'],result['violations'],result['schematic_parity'],result['erc_violations'])==(new,22,0,0,0)
assert result['ina300_rlimit_return_screen']=='PASS' and result['new_reference_gaps']==0
assert planned['status']=='PASS' and len(planned['checks'])==2573 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert sum(x['status']=='FAIL' for x in reg['reference_transitions'])==6
assert inspect['same_face_nominal_body_hit_count']==0 and inspect['required_new_supply_corridors_pass'] and inspect['source_local_pair_widths_preserved']
assert inspect['counts']=={'segments':1322,'vias':326,'footprints':215,'new_segments':41}
assert len(inspect['wheel_groups'])==1 and 'R1002.1' in inspect['wheel_groups'][0]
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==9
assert read(b/'R159F-inspection.json')['same_face_nominal_body_hit_count']==1
assert read(b/'R159G-verified/result.json')['new_reference_gaps']==1
members={x['member']:x['sha256'] for x in read(dev/'evidence/R156G/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(source/name)==sha(candidate/name)==digest,name
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
old_status=read(dev/'STATUS.json');assert old_status['board_sha256']==old and old_status['unconnected_items']==23
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();now=datetime.now(timezone.utc).isoformat()
evidence.mkdir();study.mkdir()
for p in (b/'R159H-verified').iterdir():shutil.copy2(p,evidence/p.name)
for src,dest in [('R159H-plan.json','plan.json'),('R159H-inspection.json','inspection.json'),('R159H-visual-review.json','visual_review.json'),('R159H-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dest)
shutil.copytree(b/'R159H-views',evidence/'images')
(evidence/'source_R156G.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 writer=csv.writer(f);writer.writerow(['item','description','endpoint_descriptions'])
 for n,x in enumerate(read(evidence/'drc.json')['unconnected_items'],1):writer.writerow([n,x['description'],' | '.join(y['description'] for y in x['items'])])
payloads=[];omitted=[];trials=[]
def preserve(src,rel):
 data=src.read_bytes();compress=src.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288;dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R159*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch(r'R159[A-H]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  changed=[]
  for q in sorted(p.rglob('*')):
   if not q.is_file() or q.name==board:continue
   rel=q.relative_to(p).as_posix()
   if rel in members and sha(q)==members[rel]:continue
   if rel in members:changed.append(rel)
   preserve(q,Path('raw')/p.name/rel)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':p.name=='R159H',**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'old_power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'lost_pad_connection_nets':len(a['lost_pad_connections']),
   'old_reference_loss_count':len(a['retained_trace_reference_loss']),'new_reference_gap_count':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),
   'changed_non_PCB_source_members':changed,'ERC':'0 enabled violations' if p.name in ('R159F','R159G','R159H') else 'NOT_TESTED','physical':'NOT_TESTED'})
 elif p.name!='R159H-views':
  copies=[q.parent for q in p.rglob(board)]
  for q in sorted(p.rglob('*')):
   if not q.is_file():continue
   owner=next((root for root in copies if root in q.parents),None);rel=q.relative_to(owner).as_posix() if owner else None
   if rel in members and sha(q)==members[rel]:
    omitted.append({'local_path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});continue
   preserve(q,Path('raw')/q.relative_to(b))
assert len(trials)==8
for name in ['build_trial.py','review_planned_delta.py','audit_candidate.py','copper_geometry.py','audit_ina300_return.py','verify_trial.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py']:preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R159.json'))
write(study/'summary.json',{'recorded_at_utc':now,'source_commit':commit,'source_revision':'R156G','source_sha256':old,'adopted_revision':'R159H','adopted_board_sha256':new,'candidates':trials,
 'new_connectivity':'R1002.1 joins WHEEL_VM; 23 to 22 native unconnected items. All original electrical/reference checks preserved.',
 'INA300':'Explicit same-B-face R1701.1 to actual U1701.8 return is now present; full manufacturer/parasitic/thermal qualification remains NOT_TESTED.',
 'F_G_H_review':'F passes native DRC and electrical regression but its LIMIT trace clips the nominal INA300 body by 0.000494 mm2. G removes that clip but causes a 0.010951 mm2 reference gap. H jointly shifts the existing UPS via upward 0.075 mm, preserving width, drill, ground holes and all original reference checks.',
 'supply_resolution':'New UPS sample via is outside the CAM 5 V corridor at (51.35,6.2); 3.42 mm2 In2 allocation extension connects north of a fixed ground hole. Fixed S2 via preserved; local In3 step avoids the relocated power-hole voids.',
 'MOTION_5V_control':'Deleting the existing lower 5 V via and its B trunk loses original pad/width connections: it is functional, not redundant. Diagnostic board is not a candidate.',
 'search_limits':'F-only and multilayer fixed-copper INA+ searches found no raster path within their bounds. Retain the original long INA+ trunk; no global impossibility claim.',
 'images':'H nine views actually reviewed; F nine local views viewed earlier. G images were generated but no separate full image review is claimed.',
 'remaining_unconnected_items':22,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,'not_engineering_progress':True,'manufacturing_release':False,'physical':'NOT_TESTED','goal_complete':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R156G_non_PCB_members':members,'unchanged_native_members_omitted':omitted,
 'reconstruction':'Use source R156G non-PCB members plus archived boards and the explicit metadata overlays. Compressed payloads restore exact original bytes. Diagnostic/probe boards are not design candidates.',
 'H_images':'../R159H/images','original_local_sources_preserved':True})
for row in payloads:
 q=study/row['path'];assert sha(q)==row['sha256'];data=gzip.decompress(q.read_bytes()) if row['gzip'] else q.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'native_layout_candidates':8,'stored_native_boards':sum(x['path'].endswith('.kicad_pcb.gz') for x in payloads),'all_original_byte_hashes_match':True,'source_local_trials_untouched':True})
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert source_all=={p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for name,digest in source_all.items():
 if name!=board:assert sha(source/name)==digest,name
write(evidence/'adoption.json',{'adopted_at_utc':now,'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,
 'member_checks':[{'member':p,'sha256':sha(source/p)} for p in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status={**old_status,**result};status.update({'revision':'C3 R159H','previous_candidate':'C3 R156G','previous_candidate_sha256':old,
 'strict_regression_explanation':'Raw strict audit retains FAIL for five planned footprint transforms, three non-ground via moves, 22 replaced tracks and one 3.42 mm2 power allocation extension. All 2573 exact planned checks and recorded electrical/reference regressions pass; no rule or allow-list relaxation.',
 'planned_delta_review_status':'PASS','planned_delta_check_count':2573,'electrical_regression_status':'PASS','local_visual_review':'PASS',
 'local_visual_review_explanation':'Six candidate layers and three source views actually inspected. Zero new mounted-face nominal-body hits. Six opposite/internal component projection groups reviewed individually; coupling and thermal qualification remain NOT_TESTED.',
 'new_same_face_nominal_body_projection_groups':0,'segment_count':1322,'via_count':326,'footprint_count':215,'remaining_connectivity_fraction':.55,'remaining_WHEEL_VM_groups':1,'R1002_wheel_tap_connected':True,
 'ina300_rlimit_return_evidence':'evidence/R159H/ina300-return.json','last_followup_study':'R159','latest_study_evidence':'evidence/R159_study/summary.json',
 'open_manufacturer_layout_items':[{'id':'INA300_COMPLETE_LAYOUT_QUALIFICATION','status':'NOT_TESTED','from':'R1701.1','to':'U1701.8','reason':'The missing explicit return has been corrected with a same-B-face 6.1 mm nominal centerline path. It also contacts ground fill; no isolated Kelvin, parasitic, coupling or thermal qualification is inferred.','datasheet':'TI INA300 SBOS613C section 10.1, printed pages 29-30','evidence':'evidence/R159H/visual_review.json'}],
 'goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':'R159H','unconnected_items':22,'remaining_connectivity_fraction':.55,'exact_checks':2573,'payload_count':len(payloads),'unchanged_non_PCB_source_members':77,'goal_complete':False}))
