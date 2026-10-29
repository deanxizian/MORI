"""Preserve bounded R154 studies and adopt the verified input-trunk refinement only."""
import csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';candidate=b/'R154B';base=Path('robot/.state/c3-completion/baseline')
evidence=dev/'evidence/R154B';study=dev/'evidence/R154_study'
backup=Path('robot/.state/c3-completion/baseline_R153G_before_R154B')
board='MORI_Interface_C3.kicad_pcb'
old='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
new='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(source/board)==old and sha(candidate/board)==new
assert not evidence.exists() and not study.exists() and not backup.exists()
r=read(b/'R154B-verify/result.json');reg=read(b/'R154B-verify/regression.json')
planned=read(b/'R154B-planned-delta.json');local=read(b/'R154B-local-review.json')
opposite=read(b/'R154B-opposite-projections.json')
assert (r['board_sha256'],r['unconnected_items'],r['violations'],r['schematic_parity'],r['erc_violations'])==(new,24,0,0,0)
assert planned['status']=='PASS' and len(planned['checks'])==2507 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert sum(x['status']=='FAIL' for x in reg['reference_transitions'])==6
assert local['counts']=={'segments':1302,'vias':325,'footprints':215}
assert local['same_face_body_hits']==0 and not opposite['projections']
w=next(x for x in local['power_width'] if x['width_mm']==.48)
assert all(w['candidate'][p] for p in ['C1201.1','C1202.1','C909.1','C911.1'])
assert not w['candidate']['U1201.5'] and not w['source']['C1201.1'] and not w['source']['C1202.1']
assert local['unchanged_ground_via']['source_identical']
members=sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and p.name not in [board,'MORI_Interface_C3.kicad_prl'])
assert len(members)==77
for p in members:assert (base/p).read_bytes()==(source/p).read_bytes()==(candidate/p).read_bytes(),str(p)
source_hashes={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
old_status=read(dev/'STATUS.json');assert old_status['board_sha256']==old
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
images=[{'path':'images/'+p.name,'sha256':sha(p),'svg_sha256':sha(p.with_suffix('.svg'))} for p in sorted((b/'R154B-views').glob('*.png'))]
assert len(images)==8
evidence.mkdir();study.mkdir()
for p in (b/'R154B-verify').iterdir():shutil.copy2(p,evidence/p.name)
for src,dest in [('R154B-plan.json','plan.json'),('R154B-planned-delta.json','planned-delta.json'),('R154B-local-review.json','power-review.json'),('R154B-opposite-projections.json','opposite-projections.json'),('R154B-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dest)
shutil.copytree(b/'R154B-views',evidence/'images')
write(evidence/'visual_review.json',{
 'source_sha256':old,'candidate_sha256':new,'local_status':'PASS','images_actually_viewed':images,
 'findings':[
  'Three 0.50 mm front input-trunk segments and one 0.30 mm terminal escape replace five partly overlapping 0.30 mm segments. The input-trunk turn to C1202 and branch to C1201 are direct orthogonal junctions, with no new small clearance jog.',
  'C1201 moves left 0.05 mm, with orientation and all pad definitions unchanged. The existing RAW via moves left 0.05 mm to (8.85,23.05); its 0.50/0.30 mm pad/drill remain unchanged and it contacts F and In2. No new vias.',
  'The existing GND via at (7.025,24) and every other GND via remain fixed. Its copper gap to the moved input capacitor pad is 0.217229 mm; native DRC passes the full copper/hole rules.',
  'The real filled input path to C1201 and C1202 now passes the additional 0.48 mm erosion screen, where the source failed. Existing C909/C911 paths still pass. The final U1201.5 connection is 0.30 mm wide and 0.40 mm long; no 0.48 mm full-terminal claim.',
  'Six candidate local layers and both outer source layers were actually viewed. The moved via retains its In2 contact and does not break old reference copper or any old supply/ground connectivity.',
  'No new mounted-face body crossing outside same-net pad lands, and no opposite-face nominal body projections for these four new segments. Existing opposite pads and copper are separated by the retained reference planes; this does not establish coupling or temperature margins.'
 ],
 'same_face_nominal_body_hit_count':0,'opposite_nominal_body_projections':[],
 'limits':['Local native geometry plots, not measured package envelopes or a whole-board visual acceptance.','Nominal Fab/fallback body inventory excludes solder lands as component bodies.','Six historical reference-transition findings remain.','The erosion screen is connectivity/width evidence, not an ampacity, voltage-drop, current-distribution or thermal qualification.'],
 'whole_board':'NOT_TESTED','physical':'NOT_TESTED','manufacturing_release':False})
ti=read(b/'R154-ti-reference/source.json')
write(evidence/'manufacturer_review.json',{
 'url':ti['url'],'source_pdf_sha256':ti['sha256'],'document':'TI TPS25947 SLVSFC9C, revised May 2026',
 'pages_actually_viewed':[63,73],
 'finding':'The RPW0010A drawing 4225183/A shows 0.30 by 2.40 mm power lands 5 and 6. These dimensions agree with the unchanged native U1201 input/output land bounds after its 90 degree rotation.',
 'native_input_land_bounds_mm':[9.3,24.6,11.7,24.9],
 'layout_review':'Manufacturer guidance also calls for short current paths, current and thermal sizing, quiet analog grounding and thermal/current spreading at IN/OUT. This four-trace improvement does not establish compliance with all of that guidance.',
 'scope_limit':'Only the cited power-land dimensions and pertinent layout guidance reviewed; not complete footprint, stencil, fabrication, solder-joint, current-distribution or thermal qualification.',
 'physical':'NOT_TESTED','manufacturing_release':False})
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
for p in sorted(b.glob('R154*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif p.name in ['R154A','R154B']:
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for name in ['edit_plan.json','edit_manifest.json','MORI_Interface_C3.kicad_pro']:
   q=p/name
   if q.is_file() and (name!='MORI_Interface_C3.kicad_pro' or q.read_bytes()!=(source/name).read_bytes()):preserve(q,Path('raw')/p.name/name)
  d=read(b/(p.name+'-drc.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':p.name=='R154B',**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']}})
 elif p.name!='R154B-views':
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
preserve(Path(__file__),Path('archive_and_adopt_R154.py'))
write(study/'summary.json',{'source_revision':'R153G','source_sha256':old,'adopted_revision':'R154B','adopted_sha256':new,'candidates':trials,'remaining_unconnected_items':24,'remaining_connectivity_fraction':.6,'not_engineering_progress':True,'OV_placement_studies':'Bounded independent proposals only. No group relocation or OV/RAW monitor connection adopted.','RAW_route_search':'Unchanged-copper bounded search found no path with exact native In2 whitelist. Not global unroutability.','manufacturing_release':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'accepted_images':images,'local_only':'Unchanged full native members and UI/cache files remain in local trial directories; none deleted.'})
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_sha256']
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'all_stored_and_original_byte_hashes_match':True,'source_local_trials_untouched':True})
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert {p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}==source_hashes
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for rel,digest in source_hashes.items():
 if rel!=board:assert sha(source/rel)==digest
write(evidence/'adoption.json',{'adopted_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,'member_checks':[{'member':str(p),'sha256':sha(source/p)} for p in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status=dict(old_status);status.update(r)
status.update({'revision':'C3 R154B','previous_candidate':'C3 R153G','previous_candidate_sha256':old,'strict_regression_explanation':'Raw geometry audit records five replaced tracks, one moved capacitor and one moved non-ground via. All 2507 exact planned checks and the separate electrical/reference regressions pass.','planned_delta_check_count':2507,'local_visual_review_explanation':'Six candidate layers and two source outer layers actually viewed; no new same-face nominal body crossings or opposite-body projections for the four new traces.','segment_count':1302,'via_count':325,'footprint_count':215,'input_capacitor_trunk_0_48_mm_screen':'PASS for C1201/C1202 and retained C909/C911 paths','inherited_U1201_input_0_48_mm_screen':'FAIL at the unchanged 0.30 mm native power land and 0.40 mm terminal escape; capacitor trunk is now 0.50 mm. 0.28 mm terminal screen passes.','goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':'R154B','unconnected':24,'remaining_fraction':.6,'exact_checks':2507,'archive_payloads':len(payloads),'other_native_members_unchanged':77,'goal_complete':False}))
