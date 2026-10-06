"""Preserve the current M1.49 delivery before adopting documented entry directions."""
from pathlib import Path
import datetime,hashlib,json,shutil,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
SNAP=ROOT/'mechanical/revisions/V1.2-M1.49_before_CAM_entry_fix'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert read(ROOT/'config/geometry.json')['revision']=='V1.2-M1.49'
expected='89cb07f571367bf87b627c771998d0cc0c28b873be575afdb4002c9bcf5b499f'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==expected
assert not (OUT/'preparation.json').exists(),'Preparation already recorded; inspect rather than overwrite baseline'
protected=read(OUT.parent/'neck_adoption/approval.json')['protected_hardware']
for name,h in protected.items():assert sha(ROOT/name)==h,name
oldpub=read(OUT.parent/'head_harness_M1_49/remaining_routes/publication.json')
for name,h in oldpub['files'].items():assert sha(ROOT/name)==h,name
paths=[ROOT/'config/geometry.json',ROOT/'contracts/mechanical_interfaces.json',
 ROOT/'mechanical/mori_v1_2.blend',ROOT/'mechanical/mori_assembly_animation.blend',ROOT/'mechanical/mori_electronics_detail.blend',
 ROOT/'mechanical/index.html',ROOT/'mechanical/parts.html',ROOT/'mechanical/manufacturing.html',ROOT/'mechanical/README.md',
 OUT.parent/'work_status.json',OUT.parent/'engineering_current.json',OUT.parent/'ENGINEERING.md']
for folder in ['mechanical/scripts','mechanical/reports','mechanical/renders','mechanical/animation','mechanical/exports']:
 paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
for folder in [OUT.parent/'neck_adoption',OUT.parent/'head_harness_M1_49/remaining_routes']:
 for name in ['delivery.json','publication.json','continuation_status.json']:
  p=folder/name
  if p.exists():paths.append(p)
snapshots={}
for p in sorted(set(paths)):
 rel=p.relative_to(ROOT);q=SNAP/rel;q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(q)==sha(p),rel
 else:shutil.copy2(p,q)
 h=sha(p);assert sha(q)==h,rel;snapshots[str(rel)]={'snapshot':str(q.relative_to(ROOT)),'sha256':h}
r=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_revision='V1.2-M1.49',
 source_blend_sha256=expected,snapshot_root=str(SNAP.relative_to(ROOT)),files=snapshots,protected_hardware=protected,
 scope='Model-only correction of two photo-reconstructed CAM FPC entries; no print, board datum or electrical change',
 authorization='User M1.33 instruction: model Waveshare using official dimensions plus photographs; uncertain physical mating remains excluded',
 pending_structural_candidates=['body front/rear split','C6','sliding guide v4','return clamp v3'],
 actual_command=[sys.executable,*sys.argv],script_sha256=sha(Path(__file__)))
(OUT/'preparation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAM_ENTRY_PREPARATION_PASS',len(snapshots),'snapshots',len(protected),'hardware files')
