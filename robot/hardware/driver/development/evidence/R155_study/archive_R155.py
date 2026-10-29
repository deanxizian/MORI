"""Preserve R155 independent native studies without adopting any failed candidate."""
import gzip,hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';study=dev/'evidence/R155_study';board='MORI_Interface_C3.kicad_pcb'
expected='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert sha(source/board)==expected and read(dev/'STATUS.json')['revision']=='C3 R154B'
source_hashes={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
assert not study.exists();study.mkdir();payloads=[];trials=[]
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def preserve(src,rel):
 data=src.read_bytes();compressed=src.suffix=='.kicad_pcb' or len(data)>524288
 dest=study/rel
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compressed})
for p in sorted(b.glob('R155*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch(r'R155[A-Z]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for name in ['edit_plan.json','edit_manifest.json']:
   if (p/name).is_file():preserve(p/name,Path('raw')/p.name/name)
  changed=[]
  for name,digest in source_hashes.items():
   if name==board or name.endswith(('.kicad_prl','.lck')):continue
   q=p/name;assert q.is_file(),(p.name,name)
   if sha(q)!=digest:
    changed.append(name);preserve(q,Path('raw')/p.name/name)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':False,
   **{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'lost_old_pad_connections':[{'net':x['net'],'pair_count':len(x['lost_pad_pairs'])} for x in a['lost_pad_connections']],
   'old_reference_loss_count':len(a['retained_trace_reference_loss']),
   'new_reference_gap_count':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),
   'power_width_failed_count':sum(x['status']!='PASS' for x in a['power_width']),
   'ground_pad_group_sizes':[len(g) for g in a['GND_groups']],
   'changed_other_native_members':changed,
   'erc':'NOT_REEXECUTED; schematic source unchanged','physical':'NOT_TESTED','manufacturing_release':False})
 else:
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
preserve(Path(__file__),Path('archive_R155.py'))
assert len(trials)==11
write(study/'summary.json',{
 'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_revision':'R154B','source_sha256':expected,'adopted_revision':None,'candidates':trials,
 'canonical_unconnected_items':24,'original_unconnected_items':40,'remaining_connectivity_fraction':.6,
 'fraction_is_not_engineering_progress':True,'guard_diagnostic':'V2 rotation rejection conflated track and via cutouts; see raw/R155-guard-diagnostic.json. V1 did not validate retained-via intersections. Neither study proves an accepted rotated block.',
 'partial_preparation':'R155F swaps C1301/R1021 locations, restores UV and BAT links, and gives U1301.4 a short exit through the former upper UV hole. All old electrical/reference/placement/width screens pass, but OV is unfinished and the via is dangling. It is not a canonical or fully reviewed candidate.',
 'native_crosscheck':'G/H/I connect OV but split existing supplies. Four preserved In2 supply-corridor reservations lead to J, retaining HEAD_VM/WHEEL_VM/HEAD_BUCK_IN yet fragmenting MOTION_3V3. K also fails and is not adopted.',
 'next_action':'Jointly redesign the two separated MOTION_3V3 feeds and OV transfers. Start from R154B and replay only explicit deltas; do not keep a disconnected supply or relax reference/width/keepout checks.',
 'manufacturing_release':False,'goal_complete':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'local_only':'Unchanged vendor/native source members and all complete local trial folders remain on Sol; nothing deleted.'})
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256']
 data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
 assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert {p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}==source_hashes
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'native_trial_count':len(trials),'all_stored_and_original_byte_hashes_match':True,'canonical_native_directory_unchanged':True,'source_local_trials_untouched':True})
print(json.dumps({'archived_payloads':len(payloads),'native_trials':len(trials),'adopted':None,'canonical_revision':'R154B','canonical_unconnected':24}))
