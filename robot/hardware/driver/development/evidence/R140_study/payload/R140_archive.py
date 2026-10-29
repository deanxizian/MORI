"""Freeze this turn's new trial evidence without overwriting prior archives."""
import gzip,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
base=Path('robot/.state/c3-completion/trials').resolve()
dest=Path('robot/hardware/driver/development/evidence').resolve()
canonical=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
sha=lambda data:hashlib.sha256(data).hexdigest()
assert sha(canonical.read_bytes())=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
script=Path(__file__).resolve()
for label,prefixes,extras in [('R140_study',['R140'],['R138_joint_search.py','run_R138_trial.py','R139K-ground-before-clr/searches.json'])]:
 out=dest/label;out.mkdir(exist_ok=False)
 files={script};boards=[];metrics=[]
 for name in extras:files.add(base/name)
 for obj in base.iterdir():
  if not any(obj.name.startswith(p) for p in prefixes):continue
  if obj.is_file():files.add(obj);continue
  board=obj/'MORI_Interface_C3.kicad_pcb'
  if board.exists():
   boards.append({'revision':obj.name,'local_source':str(board),'sha256':sha(board.read_bytes()),'size_bytes':board.stat().st_size,'included_in_archive':False})
   for name in ['edit_plan.json','edit_manifest.json']:
    if (obj/name).exists():files.add(obj/name)
   drc=base/(obj.name+'-drc.json');audit=base/(obj.name+'-audit.json')
   if drc.exists():
    d=json.loads(drc.read_text());row={'revision':obj.name,**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']}}
    if audit.exists():
     a=json.loads(audit.read_text());row.update({'lost_pad_nets':[x['net'] for x in a['lost_pad_connections']],'power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'ground_group_sizes':[len(g) for g in a['GND_groups']],'retained_reference_loss_rows':len(a['retained_trace_reference_loss']),'new_reference_gap_rows':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-7 for x in a['new_copper_review']),'critical_placement_failures':sum(x['status']!='PASS' for x in a['critical_placement'])})
    metrics.append(row)
  else:files.update(p for p in obj.rglob('*') if p.is_file())
 records=[]
 for f in sorted(files):
  rel=f.relative_to(base);data=f.read_bytes()
  compress=f.suffix in ['.json','.log','.svg'] and len(data)>1500
  target=out/('payload/'+str(rel)+('.gz' if compress else ''));target.parent.mkdir(parents=True,exist_ok=True)
  archived=gzip.compress(data,mtime=0) if compress else data
  target.write_bytes(archived)
  assert (gzip.decompress(target.read_bytes()) if compress else target.read_bytes())==data
  records.append({'source':str(f),'source_sha256':sha(data),'source_size_bytes':len(data),'archive':str(target.relative_to(out)),'archive_sha256':sha(archived),'compression':'gzip' if compress else 'none'})
 manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'Unadopted independent geometry/routing experiments only. No physical validation, release, manufacture, device operation, or canonical change. Full native candidate projects remain local and are not represented as included in this archive.','canonical_sha256':sha(canonical.read_bytes()),'payloads':records,'local_native_boards':sorted(boards,key=lambda x:x['revision']),'native_trial_summary':sorted(metrics,key=lambda x:x['revision'])}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'archive':label,'payloads':len(records),'native_boards_hashed':len(boards),'archive_bytes':sum((out/r['archive']).stat().st_size for r in records)}),flush=True)
