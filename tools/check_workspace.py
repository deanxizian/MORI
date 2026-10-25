#!/usr/bin/env python3
"""Check project separation, current paths and preserved asset identities offline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]


def check(root, allow_lfs_pointers=False):
    errors=[]
    def require(ok,message):
        if not ok: errors.append(message)
    projects=json.loads((root/'projects.json').read_text())['projects']
    require({p['id'] for p in projects}=={'robot','test_rig'},'Expected the two independent projects')
    manifests={p['id']:json.loads((root/p['manifest']).read_text()) for p in projects}
    for p in projects:
        require(p['id']==manifests[p['id']]['project_id'],'Project identity mismatch: '+p['id'])
        require(not manifests[p['id']]['manufacturing_release'],'Publication must not imply manufacturing release')
        require((root/p['path']/'README.md').is_file(),'Missing project entry: '+p['path'])
    require(manifests['robot']['mechanical_model']=='mechanical/mori.blend','Unstable main-model entry')
    require(manifests['robot']['software_implementation_version']=='1.2.0-dev.1','Organization must not upgrade robot software')
    require(manifests['test_rig']['software_revision']=='v184','Test rig latest source missing')
    require(manifests['test_rig']['mechanical_revision']=='R59','Comparison must not silently replace adopted rig')
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root,text=True).split('\0'))
    for old in ('apps/','backend/','config/','contracts/','docs/','firmware/','hardware/','mechanical/','software/','simulation/','refs/'):
        require(not any(p.startswith(old) for p in tracked),'Published legacy project root remains: '+old)
    for doc in ('README.md','VERSIONING.md','HANDOFF.md'):
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',(root/doc).read_text()):
            url=urlsplit(target.strip('<>'))
            if url.scheme or url.netloc or not url.path: continue
            resolved=(root/unquote(url.path)).resolve()
            if not resolved.is_relative_to(root):
                errors.append('Link outside repository: '+target);continue
            path=resolved.relative_to(root).as_posix()
            require(path in tracked or any(p.startswith(path.rstrip('/')+'/') for p in tracked),'Unpublished link: '+doc+': '+target)
    for project in manifests.values():
        require(project['project_version'] in (root/'README.md').read_text(),'Root version table stale')
    receipt=json.loads((root/'robot/docs/organization/path_migration.json').read_text())
    protected=0
    for item in receipt['entries']:
        # Geometry, purchased hardware archives and frozen evidence must survive renaming exactly.
        old=item['old'];path=root/item['new']
        frozen=old.startswith(('mechanical/input_assets/','mechanical/reports/','docs/review_evidence/','docs/evidence/','docs/archive/','hardware/driver/evidence/','hardware/driver/publication/','software/reference_sources/'))
        source_contract=old.startswith('contracts/') or old in ('config/geometry.json','MORI_SPEC_V1_2.md','01_CODEX_MECHANICAL.md')
        if frozen or source_contract or path.suffix.lower() in ('.blend','.stl','.step','.stp','.npz','.zip','.png','.jpg','.jpeg','.mp4','.kicad_pcb','.kicad_sch','.c','.h'):
            if not path.is_file():
                errors.append('Missing preserved file: '+item['new']);continue
            data=path.read_bytes()
            if data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                ok=allow_lfs_pointers and f"oid sha256:{item['before_sha256']}\n".encode() in data
            else: ok=hashlib.sha256(data).hexdigest()==item['before_sha256']
            require(ok,'Preserved bytes differ: '+item['new']);protected+=1
    return dict(status='FAIL' if errors else 'PASS',scope='Repository organization and provenance only; no hardware I/O',protected_files=protected,errors=errors)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-lfs-pointers',action='store_true')
    args=parser.parse_args()
    result=check(ROOT,args.allow_lfs_pointers)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(result['status']!='PASS')
