"""Package verified current core outputs plus their complete published inputs."""
from pathlib import Path
import argparse, datetime, hashlib, json, shutil, zipfile
PROJECT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(project,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe package path: '+name)
    return project/p

def check(project):
    root=project/'mechanical';reports=root/'reports'
    validation=read(reports/'validation.json')
    if validation['counts']['FAIL']:raise ValueError('Failed geometry checks')
    if validation.get('source_blend_sha256')!=sha(root/'mori_v1_2.blend'):raise ValueError('Validation model changed')
    if read(reports/'delivery_consistency.json')['status']!='PASS':raise ValueError('Delivery consistency has not passed')
    exports=read(reports/'export_manifest.json')
    if exports['candidate_count']!=exports['exported_count']:raise ValueError('STL export incomplete')
    for row in exports['parts']:
        if row['status']!='PASS' or sha(safe(root,row['file']))!=row['sha256']:raise ValueError('STL changed: '+row['id'])
    for name,digest in read(reports/'build_manifest.json')['input_sha256'].items():
        if sha(safe(project,name))!=digest:raise ValueError('Build source changed: '+name)
    for row in read(reports/'render_manifest.json'):
        p=root/'renders'/(row['view']+'.png')
        if sha(p)!=row['image_sha256'] or p.stat().st_size!=row['image_bytes']:raise ValueError('Rendered image changed: '+row['view'])

def collect(project):
    root=project/'mechanical';reports=root/'reports'
    names=set(read(reports/'build_manifest.json')['input_sha256'])
    native='hardware/v1_2/native_projects/manifest.json';names.add(native)
    for bundle in read(project/native)['projects']:
        names.add(bundle['archive'])
        if sha(safe(project,bundle['archive']))!=bundle['sha256']:raise ValueError('Native archive changed')
        for item in bundle['files']:
            if sha(safe(project,item['path']))!=item['sha256']:raise ValueError('Native file differs: '+item['path'])
            names.add(item['path'])
    names.update(['AGENTS.md','MORI_SPEC_V1_2.md','01_CODEX_MECHANICAL.md','config/geometry.json','contracts/mechanical_interfaces.json','contracts/components.json','docs/CURRENT_STATUS.md','mechanical/README.md','mechanical/current_report.html','mechanical/mori_v1_2.blend'])
    # Restore manifest pins nested CAD/PDF/photo inputs read by the builders.
    manifest=read(project/'docs/archive_assets.json')
    for group in ('mechanical-data','mechanical-build-inputs','legacy-helpers'):
        for item in manifest['groups'][group]:
            p=safe(project,item['path'])
            if sha(p)!=item['sha256']:raise ValueError('Restored input differs: '+item['path'])
            names.add(item['path'])
    names.update(str(p.relative_to(project)) for p in (root/'scripts').glob('*.py'))
    names.update(str(p.relative_to(project)) for p in (root/'input_assets').iterdir() if p.is_file())
    for f in ('build_manifest','validation','delivery_consistency','export_manifest','render_manifest','current_report','head_shell_cleanup','imu_mount_transform'):
        names.add('mechanical/reports/'+f+'.json')
    names.update('mechanical/'+row['file'] for row in read(reports/'export_manifest.json')['parts'])
    names.update('mechanical/renders/'+row['view']+'.png' for row in read(reports/'render_manifest.json'))
    for name in names:
        if not safe(project,name).is_file():raise FileNotFoundError('Required current input/output missing: '+name)
    return sorted(names)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-parent',required=True,type=Path);parser.add_argument('--release-name');args=parser.parse_args()
    check(PROJECT);revision=read(PROJECT/'config/geometry.json')['revision']
    name=args.release_name or 'MORI_'+revision.replace('.','_')
    if Path(name).name!=name or name in ('.','..'):raise ValueError('Invalid release name')
    dest=args.output_parent/name;archive=args.output_parent/(name+'.zip')
    if dest.exists() or archive.exists():raise FileExistsError('Existing delivery retained: '+str(dest))
    names=collect(PROJECT)
    for name in names:
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/name,target)
    (dest/'README.md').write_text(f'''# MORI {revision} mechanical prototype\n\nOpen mechanical/current_report.html for executed evidence and mechanical/mori_v1_2.blend for the current assembly. Geometry PASS is not manufacturing or physical qualification; see docs/CURRENT_STATUS.md.\n\nRebuild the current core with `python3 mechanical/scripts/run_all.py --core` after installing Blender/manifold3d as documented. The package includes the exact build inputs, published nested CAD/PDF/photo sources and generated STL/render outputs. CAD Python is configured through MORI_CAD_PYTHON. Historical comparison blends and external tool runtimes are not bundled; optional historical comparison stages may remain BLOCKED. This package is not a supplier production release.\n''')
    check(dest)
    manifest={'revision':revision,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','scope':'Current input/output integrity; PROTOTYPE / UNVALIDATED; manufacturing_release=false','files':{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}}
    (dest/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(args.output_parent))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Package ZIP CRC failed')
    print(json.dumps({'status':'PASS','archive':str(archive),'files':len(manifest['files'])+1,'bytes':archive.stat().st_size,'sha256':sha(archive)}))
if __name__=='__main__':main()
