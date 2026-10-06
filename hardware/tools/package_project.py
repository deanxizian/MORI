#!/usr/bin/env python3
"""Archive the hardware addition to the existing MORI mechanical project."""
from pathlib import Path
import hashlib, json, zipfile
R=Path(__file__).resolve().parents[1]
release=R/'releases';release.mkdir(exist_ok=True)
bundle=release/'MORI_Hardware_RevA0.4.zip'
files=[]
for p in sorted(R.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(R)
    if set(rel.parts)&{'build','managed_components','releases','archive','__pycache__'}:continue
    if any(part.endswith('.dSYM') for part in rel.parts):continue
    if p.name in {'test_core','.DS_Store','sdkconfig.old'} or p.suffix in {'.pyc','.kicad_prl'}:continue
    files.append(p)
hashes={str(p.relative_to(R.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,str(p.relative_to(R.parent)))
    z.writestr('BUNDLE_README.txt',
        'MORI hardware RevA0.4 / HW-SW-0.4, 2026-09-21\n'
        'Extract into a COPY of the existing MORI project. Do not overwrite a working software branch.\n'
        'Start at hardware/README.md and hardware/handoff/.\n'
        'The mechanical params/models/exports already belong to the original MORI project; they are not replaced here.\n'
        'Calculation resynchronization requires the original params.json, reports/ and exports/stl/.\n'
        'Native KiCad source and local symbol/footprint libraries are included. PCB UNROUTED; NOT FOR FABRICATION.\n'
        'Firmware binaries, build cache and downloaded ESP-IDF components are excluded. Restore locked dependencies for build.\n'
        'All physical tests NOT_TESTED; no hardware was flashed or energized.\n')
    z.writestr('FILE_SHA256.json',json.dumps(hashes,indent=2,ensure_ascii=False)+'\n')
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(p)).hexdigest()==h for p,h in hashes.items())
manifest=dict(version='RevA0.4 / HW-SW-0.4',filename=bundle.name,
              size_bytes=bundle.stat().st_size,sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
              project_file_count=len(files),archive_integrity='PASS',physical_validation='NOT_TESTED',
              board_fabrication_allowed=False)
(release/'release_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
