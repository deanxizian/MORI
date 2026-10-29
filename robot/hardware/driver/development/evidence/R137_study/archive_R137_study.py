"""Freeze selected R137 diagnostics with byte checks; do not copy/adopt a candidate PCB."""
from pathlib import Path
import gzip,hashlib,json,datetime
base=Path('robot/.state/c3-completion/trials');out=Path('robot/hardware/driver/development/evidence/R137_study');out.mkdir(exist_ok=False)
def sha(b):return hashlib.sha256(b).hexdigest()
files=[x for x in base.glob('R137*') if x.is_file() and x.suffix in ['.json','.py','.log']]
for folder in ['R137C-route-search','R137D-power-bridges','R137D-cam-repair-search','R137C-cam-preserving-search','R137D-cam-soft-obstacle','R137D-cam-other-signal-obstacle','R137G-cam-repair-search','R137G-power-bridges','R137G-cam-native-search','R137H-cam-repair-search','R137J-power-preserving-search']:
 files.extend((base/folder).glob('*.json'))
files += [base/'R137C/face_transform_readback.json',base/'R137C/edit_manifest.json']
files += list((base/'R137K-views').glob('*'))
files.append(Path(__file__))
rows=[]
for src in sorted(set(files)):
 assert src.is_file(),src
 raw=src.read_bytes();rel=src.relative_to(base);z=src.suffix=='.svg' or (len(raw)>16000 and src.suffix in ['.json','.log'])
 dest=out/(str(rel)+('.gz' if z else ''));dest.parent.mkdir(parents=True,exist_ok=True)
 payload=gzip.compress(raw,compresslevel=9,mtime=0) if z else raw;dest.write_bytes(payload)
 assert (gzip.decompress(dest.read_bytes()) if z else dest.read_bytes())==raw
 rows.append({'source_local':str(src),'archive':str(dest.relative_to(out)),'source_sha256':sha(raw),'source_bytes':len(raw),'archive_sha256':sha(payload),'archive_bytes':len(payload),'encoding':'gzip' if z else 'identity'})
boards=[]
for rev in ['R137A','R137B','R137C','R137D','R137G','R137H','R137I','R137J','R137K']:
 f=base/rev/'MORI_Interface_C3.kicad_pcb';row={'revision':rev,'local_board':str(f),'board_sha256':sha(f.read_bytes()),'native_board_archived':False,'adopted':False}
 report=base/(rev+'-refilled-drc.json')
 if report.exists():
  d=json.loads(report.read_text());row['native']={k:len(d.get(k,[])) for k in ['unconnected_items','violations','schematic_parity']}
 boards.append(row)
canonical=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert sha(canonical.read_bytes())=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
manifest={'archived_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'adopted_candidate':'R134N','canonical_sha256':sha(canonical.read_bytes()),'scope':'Rejected/unadopted placement, construction, route-search and native-fill studies. No manufacturing or physical qualification. Complete local native trial directories are preserved but not copied into this archive. Source hashes alone do not make absent trial boards available on another machine.','files':rows,'local_trial_boards':boards,'viewed_images':['R137K-views/F.Cu.png','R137K-views/In3.Cu.png','R137K-views/B.Cu.png'],'image_scope':'Rendered from native planar geometry, not KiCad screenshots or complete installed-part models. F.Cu trace at y=15.4 clears nominal L701 Fab by only 0.05 mm; the BOM maximum 8.5 mm body dimension in this axis would overlap that trace by 0.10 mm. No physical clearance or body-avoidance acceptance is claimed.'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'files':len(rows),'archive_bytes':sum(r['archive_bytes'] for r in rows),'canonical_unchanged':True,'path':str(out)},ensure_ascii=False))
