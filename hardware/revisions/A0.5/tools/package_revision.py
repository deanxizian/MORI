#!/usr/bin/env python3
"""Package only the A0.5 increment; never include compiler/tool caches or binaries."""
from pathlib import Path
import json,hashlib,zipfile,datetime
R=Path(__file__).resolve().parents[1];ROOT=R.parents[2]
a=json.loads((R/'reports/audit.json').read_text())
assert not any(a['native_DRC_counts'].values())
assert a['firmware_build']['exit_code']==0 and a['fabrication_allowed'] is False
exclude={'build','managed_components','__pycache__','.git'}
items=[]
for p in sorted(R.rglob('*')):
    rel=p.relative_to(R)
    if not p.is_file() or any(s in exclude for s in rel.parts):continue
    if p.suffix in ['.zip','.jar','.pyc','.kicad_prl','.blend1','.bin','.elf','.map']:continue
    if p.name=='sdkconfig.old' or p.name=='RELEASE_MANIFEST.json':continue
    if rel.parts[0]=='reports' and p.name.startswith('test_') and not p.suffix:continue
    if p.name=='esp_reference_redirect.html':continue  # failed download, not a source CAD archive
    items.append((p,'hardware/revisions/A0.5/'+str(rel)))
handoff=ROOT/'hardware/handoff/A0.5_硬件增量通知.md'
items.append((handoff,'hardware/handoff/'+handoff.name))
records=[{'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,name in items]
manifest={'revision':'A0.5','kind':'increment to existing MORI project','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'files':records,'manifest_self_excluded_from_hash_list':True,
    'physical_tests':'NOT_TESTED','fabrication_allowed':False,
    'excluded':'IDF build/managed components, executables, Java/router caches, old ZIPs, UI caches, failed HTML download'}
m=R/'RELEASE_MANIFEST.json';m.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
items.append((m,'hardware/revisions/A0.5/RELEASE_MANIFEST.json'))
release=ROOT/'hardware/releases/MORI_Hardware_RevA0.5.zip'
with zipfile.ZipFile(release,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p,name in items:z.write(p,name)
with zipfile.ZipFile(release) as z:
    assert z.testzip() is None
    for record in records:assert hashlib.sha256(z.read(record['path'])).hexdigest()==record['sha256']
digest=hashlib.sha256(release.read_bytes()).hexdigest()
release.with_suffix('.zip.sha256').write_text(digest+'  '+release.name+'\n')
print(json.dumps({'file':str(release),'files':len(items),'bytes':release.stat().st_size,'sha256':digest,'zip_hash_audit':'PASS'},indent=2))
