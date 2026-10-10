"""Publish verified M1.54 files without rewriting research history or hardware."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'scripts'))
from pipeline_evidence import verify_pipeline_execution, verify_delivery_stamp

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

source=ROOT/'mori_v1_2.blend';digest=sha(source)
assert load(PROJECT/'config/geometry.json')['revision']=='V1.2-M1.54'
core=verify_pipeline_execution(PROJECT)
verify_delivery_stamp(PROJECT,load(ROOT/'reports/delivery_consistency.json'))
validation=load(ROOT/'reports/validation.json')
assert validation['source_blend_sha256']==digest and validation['counts']['FAIL']==0
scope=load(ROOT/'reports/cam_orientation_validation.json')
services=load(ROOT/'reports/cam_right_service_validation.json')
for r in [scope,services]:assert r['status']=='PASS' and r['source_blend_sha256']==digest
assert scope['scope']['unchanged_native_parts']==198
baseline=load(ROOT/'input_assets/M1_54_CAM_baseline.json')
protected={n:h for n,h in baseline['protected_hardware'].items()
           if not ('__pycache__' in Path(n).parts and Path(n).suffix=='.pyc')}
assert all(sha(PROJECT/n)==h for n,h in protected.items())
assert all(sha(PROJECT/n)==h for n,h in baseline['STL_sha256'].items())

records=load(HERE/'commands.json')
expected=['body_sequence','electronics','electronics_check','review_images','animation_build',
          'animation_native','animation_video','animation_check','animation_cam_readback']
assert [r['stage'] for r in records]==expected
for r in records:
    assert r['returncode']==0 and r['source_blend_sha256']==digest
    assert sha(ROOT/r['log'])==r['log_sha256']
for name in ['body_split_validation','electronics_detail_validation']:
    assert load(ROOT/'reports'/f'{name}.json')['status']=='PASS'
assert load(ROOT/'reports/electronics_detail_manifest.json')['source_main_sha256']==digest
animation=load(ROOT/'animation/manifest.json');av=load(ROOT/'animation/validation.json')
assert animation['source_blend_sha256']==digest and animation['rendered_video'] and av['status']=='PASS'
assert animation['animation_blend_sha256']==sha(ROOT/'mori_assembly_animation.blend')
assert animation['video']['sha256']==av['video']['sha256']==sha(ROOT/'animation/MORI_assembly.mp4')
ac=load(HERE/'animation_cam_readback.json')
assert ac['status']=='PASS' and ac['source_blend_sha256']==digest
assert ac['animation_sha256']==sha(ROOT/'mori_assembly_animation.blend')
render=load(HERE/'render_manifest.json');assert render['source_blend_sha256']==digest
for r in render['images']:assert sha(HERE/r['file'])==r['sha256']

save(ROOT/'animation/commands.json',[r for r in records if r['stage'].startswith('animation_')])
subprocess.run([sys.executable,str(ROOT/'scripts/publish_animation_update.py')],cwd=PROJECT,check=True)
files=[HERE/'README.md',HERE/'index.html',HERE/'commands.json',HERE/'animation_cam_readback.json',
       source,ROOT/'mori_electronics_detail.blend',ROOT/'mori_assembly_animation.blend',
       ROOT/'animation/MORI_assembly.mp4',ROOT/'reports/cam_orientation_validation.json',
       ROOT/'reports/cam_right_service_validation.json']
receipt=dict(status='PASS',revision='V1.2-M1.54',animation_revision=animation['animation_revision'],
    published_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_blend_sha256=digest,
    scope=scope['scope'],protected_hardware_files=len(protected),changed_hardware_files=[],
    STL_files_unchanged=len(baseline['STL_sha256']),validation_counts=validation['counts'],
    full_harness='BLOCKED',physical_validation='NOT_TESTED',manufacturing_release=False,
    files={str(p.relative_to(PROJECT)):sha(p) for p in files})
save(HERE/'delivery.json',receipt)
assets=load(PROJECT/'docs/current_assets.json');assets['snapshot_date']='2026-10-08';assets['mechanical_revision']='V1.2-M1.54'
for a in assets['assets']:
    if a.get('storage','').startswith('ARCHIVE'):continue
    p=PROJECT/a['path'];a['bytes']=p.stat().st_size;a['sha256']=sha(p)
    if p.name in ['mori_assembly_animation.blend','MORI_assembly.mp4']:
        a['scope']='Rebuilt and read back from current M1.54; M1.54-A1 assembly presentation, not full wired assembly qualification.'
    elif p.name=='mori_electronics_detail.blend':
        a['scope']='Rebuilt from current M1.54 and checked per reference against the source main model.'
save(PROJECT/'docs/current_assets.json',assets)
print('CURRENT_M1_54_PUBLISHED',digest,validation['counts'],flush=True)
