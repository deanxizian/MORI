"""Archive R153 studies and adopt G into the independent development entry only."""
import csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';candidate=b/'R153G';base=Path('robot/.state/c3-completion/baseline')
evidence=dev/'evidence/R153G';study=dev/'evidence/R153_study';backup=Path('robot/.state/c3-completion/baseline_R152O_before_R153G')
board='MORI_Interface_C3.kicad_pcb';old='7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9';new='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(source/board)==old and sha(candidate/board)==new
assert not evidence.exists() and not study.exists() and not backup.exists()
r=read(b/'R153G-verify/result.json');reg=read(b/'R153G-verify/regression.json');planned=read(b/'R153G-planned-delta.json');inspection=read(b/'R153G-inspection.json');power=read(b/'R153G-power-review.json')
assert (r['board_sha256'],r['unconnected_items'],r['violations'],r['schematic_parity'],r['erc_violations'])==(new,24,0,0,0)
assert planned['status']=='PASS' and len(planned['checks'])==2517 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert sum(x['status']=='FAIL' for x in reg['reference_transitions'])==6
assert inspection['same_face_nominal_body_hit_count']==0 and inspection['counts']=={'segments':1303,'vias':325,'footprints':215,'new_segments':10}
assert len(inspection['HEAD_6V_RAW_groups'])==2 and ['R1304.2'] in inspection['HEAD_6V_RAW_groups']
w=next(x for x in power['new_supply_width_checks'] if x['width_mm']==.48)
assert all(w['new_C909_paths'].values()) and all(w['new_via_paths'].values())
assert power['new_via_native_contact_layers']==['In2.Cu','B.Cu']
members=sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and p.name not in [board,'MORI_Interface_C3.kicad_prl'])
assert len(members)==77
for p in members:assert (base/p).read_bytes()==(source/p).read_bytes()==(candidate/p).read_bytes(),str(p)
source_hashes={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
old_status=read(dev/'STATUS.json');assert old_status['board_sha256']==old
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();now=datetime.now(timezone.utc).isoformat()
images=[{'path':'images/'+p.name,'sha256':sha(p),'svg_path':'images/'+p.with_suffix('.svg').name,'svg_sha256':sha(p.with_suffix('.svg'))} for p in sorted((b/'R153G-views').glob('*.png'))]
assert len(images)==10
projection_reviews={
 'TH1501':'New In2 output allocation passes beneath the front NTC with intervening In1 ground. Its footprint, F copper and local temperature interface remain fixed. Changed copper spreading must be included in later thermal calibration; temperature response and trip behavior are NOT_TESTED.',
 'C909':'The new In2 branch is the same 6 V reservoir net beneath the rotated back capacitor. Back pad escape stays outside its nominal body; existing ground remains connected and the In4 return plane is retained. Effective biased capacitance, ripple current, barrel current and loop parasitics remain unqualified.',
 'R715':'The In2 allocation projects beneath the existing back CAM current-limit resistor, separated by In3/In4. Existing ILM copper, ground connection and trace reference are preserved. This is not a noise-injection or current-limit-accuracy qualification.',
 'R1411':'The new allocation reaches part of the back 10 ohm pulse resistor projection. The original HEAD_VM feed remains connected at all fifty old width screens; its hole retains 0.80/0.40 mm. Neither the new plane nor geometry screening establishes pulse energy, hot-spot temperature or capacitor thermal life.',
 'C1204':'A small part of the added In2 allocation lies below the back DVDT capacitor projection. Existing timing-net copper and ground are unchanged and separated by the retained In4 reference plane. Turn-on timing and capacitive injection remain NOT_TESTED.'}
assert set(projection_reviews)=={x['reference'] for x in power['added_In2_copper_nominal_projections']}
evidence.mkdir();study.mkdir()
for p in (b/'R153G-verify').iterdir():shutil.copy2(p,evidence/p.name)
for src,dest in [('R153G-plan.json','plan.json'),('R153G-planned-delta.json','planned-delta.json'),('R153G-inspection.json','inspection.json'),('R153G-power-review.json','power-review.json'),('R153G-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dest)
shutil.copytree(b/'R153G-views',evidence/'images')
write(evidence/'visual_review.json',{'board_sha256':new,'local_status':'PASS','images_actually_viewed':images,'source_comparison_images':[{'path':'../R153_study/raw/R153-source-views/'+p.name,'sha256':sha(p)} for p in sorted((b/'R153-source-views').glob('*.png'))],
 'findings':['C909 is translated from (3.85,17.75) to (3.85,18.4) and rotated from -90 to 180 degrees. C911 and all fixed interfaces remain unchanged.','Ten new segments replace seven old segments; no new mounted-face nominal body crossing outside same-net pad lands. The final HEAD_VM back tail is one straight 0.60 mm segment, removing the F trial small end jog.','The old HEAD_VM via moves from (6.65,17.955) to (6.6,17.8) with 0.80/0.40 mm sizes retained; its filled In2 feed remains intact. All original ground vias remain unchanged.','A new 0.50/0.30 mm RAW via at (4.55,17.05) contacts B and In2. The capacitor path uses 0.50 mm back copper; the short direction changes around that transfer preserve clearances and both nearby old reference paths.','The front output feed now goes directly from the L901-side copper to C904.1, then vertically to the original (11.5,22.8) via with 0.50 mm copper.','The HEAD_6V_RAW_LOCAL outline grows by exactly 15.63 mm2. Priority 34, 0.40 mm clearance, 0.20 mm fill minimum and all thermal/native constraints are unchanged. Actual highlighted fills show the RAW corridor continuous and the adjacent HEAD_VM feed retained.','New C909 and via paths to C911, C904, L901 and all three original local RAW vias pass 0.48 mm erosion. The inherited 0.30 mm U1201 input branch passes 0.28 mm and remains below a 0.48 mm corridor in both source and candidate.','All fifty power-width, 155 GND, 63 adjacency and old/new trace-reference regressions pass. Six historical transition flags remain.'],
 'same_face_nominal_body_hit_count':0,'new_inner_power_projections':[dict(x,review=projection_reviews[x['reference']],coupling_and_thermal='NOT_TESTED; bounded geometry and original references reviewed') for x in power['added_In2_copper_nominal_projections']],
 'limits':['Native-geometry diagnostic plots, not screenshots or dimensional measurements.','Nominal Fab/fallback bodies are not measured or manufacturer maximum envelopes.','Plots do not depict every PTH drill cut distinctly; native pad/drill geometry governs.','Trace-reference checks are not a blanket qualification of all expanded power-plane return geometry.','Retained historical connector escape exceptions elsewhere on the board are not reclassified by this local zero-new-hit result.','Whole-board routing, supply rating, thermal/EMC/parasitics, mechanical integration and physical tests remain open.'],'whole_board':'NOT_TESTED','physical':'NOT_TESTED','manufacturing_release':False})
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 writer=csv.writer(f);writer.writerow(['item','description','endpoint_descriptions'])
 for i,x in enumerate(read(evidence/'drc.json')['unconnected_items'],1):writer.writerow([i,x['description'],' | '.join(y['description'] for y in x['items'])])
payloads=[];trials=[]
def preserve(src,rel):
 data=src.read_bytes();compress=src.suffix=='.kicad_pcb' or len(data)>524288
 dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R153*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif p.name in ['R153'+x for x in 'ABCDEFG']:
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for name in ['edit_plan.json','edit_manifest.json','MORI_Interface_C3.kicad_pro']:
   q=p/name
   if q.is_file() and (name!='MORI_Interface_C3.kicad_pro' or q.read_bytes()!=(source/name).read_bytes()):preserve(q,Path('raw')/p.name/name)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':p.name=='R153G',**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'old_power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'lost_connection_nets':len(a['lost_pad_connections']),'retained_reference_loss_count':len(a['retained_trace_reference_loss']),'new_reference_gap_count':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review'])})
 elif p.name!='R153G-views':
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
preserve(b/'R152_render_highlight.py',Path('raw/helpers/R152_render_highlight.py'))
preserve(Path(__file__),Path('archive_and_adopt_R153.py'))
write(study/'summary.json',{'source_revision':'R152O','source_sha256':old,'adopted_revision':'R153G','adopted_sha256':new,'candidates':trials,'remaining_unconnected_items':24,'remaining_connectivity_fraction':.6,'not_engineering_progress':True,'manufacturing_release':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'accepted_images':images,'local_only':'Full unchanged native project members and UI/cache files remain in all local trials; none deleted.'})
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_sha256']
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'all_stored_and_original_byte_hashes_match':True,'source_local_trials_untouched':True})
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert {p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}==source_hashes
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for rel,digest in source_hashes.items():
 if rel!=board:assert sha(source/rel)==digest
write(evidence/'adoption.json',{'adopted_at_utc':now,'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,'member_checks':[{'member':str(p),'sha256':sha(source/p)} for p in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status=dict(r);status.update({k:v for k,v in old_status.items() if k.startswith('remaining_')})
status.update({'revision':'C3 R153G','status':'INDEPENDENT_DEVELOPMENT_CANDIDATE','published_revision':'C3 R108P','adopted_in_main_model':False,'previous_candidate':'C3 R152O','previous_candidate_sha256':old,'strict_regression_explanation':'Raw audit retains FAIL for seven replaced tracks, one moved capacitor and non-ground power via, and the explicit 15.63 mm2 allocation expansion. Exact planned review passes 2517 checks and electrical/reference regression passes.','step_regression_status':'FAIL','planned_delta_review_status':'PASS','planned_delta_check_count':2517,'electrical_regression_status':'PASS','local_visual_review':'PASS','local_visual_review_explanation':'Ten final local native plots and four source views actually viewed. No new mounted-face nominal body crossings outside same-net pads; five inner power projections reviewed with explicit coupling and thermal limits.','whole_board_route_style':'NOT_TESTED','new_same_face_nominal_body_projection_groups':0,'segment_count':1303,'via_count':325,'footprint_count':215,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.6,'connectivity_fraction_is_not_engineering_progress':True,'remaining_HEAD_6V_RAW_groups':2,'C909_C911_connected_to_output':True,'new_capacitor_branch_0_48_mm_screen':'PASS','inherited_U1201_input_0_48_mm_screen':'FAIL in source and candidate; original 0.30 mm branch retained, 0.28 mm screen passes','battery_sampling_chain_complete':False,'goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':'R153G','unconnected':24,'remaining_fraction':.6,'exact_checks':2517,'archive_payloads':len(payloads),'other_native_members_unchanged':77,'goal_complete':False}))
