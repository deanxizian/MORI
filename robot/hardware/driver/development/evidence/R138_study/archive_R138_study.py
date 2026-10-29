"""Freeze R138 placement and blocked-route diagnostics without adopting a PCB."""
import datetime,gzip,hashlib,json
from pathlib import Path
base=Path('robot/.state/c3-completion/trials').resolve();out=Path('robot/hardware/driver/development/evidence/R138_study');out.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
files=[f for f in base.glob('R138*') if f.is_file() and f.suffix in ['.py','.json','.log']]
for folder in ['R138A-route-search','R138A-d3-layered-search','R138A-adc-soft-obstacle','R138A-adc-shorter-diagnostic','R138A-d3-back-diagnostic','R138A-via-reference-diagnostic']:
 files.extend((base/folder).glob('*.json'))
files.append(Path(__file__).resolve());rows=[]
for src in sorted(set(files)):
 raw=src.read_bytes();z=len(raw)>16000 and src.suffix in ['.json','.log'];dest=out/(str(src.relative_to(base))+('.gz' if z else ''));dest.parent.mkdir(parents=True,exist_ok=True);payload=gzip.compress(raw,compresslevel=9,mtime=0) if z else raw;dest.write_bytes(payload)
 assert (gzip.decompress(dest.read_bytes()) if z else dest.read_bytes())==raw
 rows.append({'source_local':str(src),'archive':str(dest.relative_to(out)),'source_sha256':sha(raw),'source_bytes':len(raw),'archive_sha256':sha(payload),'archive_bytes':len(payload),'encoding':'gzip' if z else 'identity'})
board=base/'R138A/MORI_Interface_C3.kicad_pcb';d=json.loads((base/'R138A-refilled-drc.json').read_text());reg=json.loads((base/'R138A-step.json').read_text())
canonical=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert sha(canonical.read_bytes())=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
m={'archived_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'canonical_candidate':'R134N','canonical_sha256':sha(canonical.read_bytes()),'scope':'Independent, unadopted placement and diagnostic studies; no release or physical validation. Complete local native trial boards are retained locally, not included here. Search-proposal hashes do not replace absent boards on another machine.','files':rows,'local_trial_board':{'path':str(board),'sha256':sha(board.read_bytes()),'archived':False,'adopted':False,'native':{k:len(d.get(k,[])) for k in ['unconnected_items','violations','schematic_parity']},'power_width_passes':sum(r['status']=='PASS' for r in reg['power_width']),'power_width_total':len(reg['power_width']),'critical_placement_passes':sum(r['status']=='PASS' for r in reg['critical_placement']),'critical_placement_total':len(reg['critical_placement']),'ground_pad_group_sizes':[len(g) for g in reg['GND_groups']],'retained_reference_losses':len(reg['retained_trace_reference_loss']),'lost_pad_connection_nets':[x['net'] for x in reg['lost_pad_connections']]}}
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'files':len(rows),'bytes':sum(r['archive_bytes'] for r in rows),'board':m['local_trial_board']},ensure_ascii=False))
