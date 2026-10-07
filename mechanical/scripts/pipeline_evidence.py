"""Filesystem-only guards shared by the CLI and evidence tests (no bpy)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def restored_build_inputs(manifest):
    """Explicit current source groups; legacy reports/A0/runtime caches are optional."""
    groups=manifest['groups']
    rows=list(groups.get('mechanical-build-inputs', []))
    rows += [row for row in groups.get('mechanical-data', []) if row['path'].startswith('mechanical/sources/')]
    return {row['path']:row for row in rows}.values()

DELIVERY_EVIDENCE_FILES=(
    'mechanical/mori_v1_2.blend',
    *('mechanical/reports/'+name+'.json' for name in (
        'build_manifest','validation','export_manifest','render_manifest',
        'structure_changes','module_assembly','wheel_metal_export')),
)

def verify_delivery_stamp(project, delivery):
    recorded=delivery.get('evidence_sha256', {})
    if set(recorded)!=set(DELIVERY_EVIDENCE_FILES):raise ValueError('Delivery evidence fingerprint missing/incomplete')
    for name,digest in recorded.items():
        path=Path(project)/name
        if not path.is_file() or sha(path)!=digest:raise ValueError('Stale delivery evidence: '+name)

def current_inputs(project):
    project=Path(project)
    build=json.loads((project/'mechanical/reports/build_manifest.json').read_text())
    paths=set(build['input_sha256'])
    paths.update(str(p.relative_to(project)) for p in (project/'mechanical/scripts').glob('*.py'))
    paths.update(str(p.relative_to(project)) for p in (project/'mechanical/input_assets').glob('*') if p.is_file())
    if (project/'tools/restore_archive_assets.py').is_file():paths.add('tools/restore_archive_assets.py')
    manifest=project/'docs/archive_assets.json'
    if manifest.exists():
        paths.add('docs/archive_assets.json')
        for entry in restored_build_inputs(json.loads(manifest.read_text())):
            target=project/entry['path']
            if not target.is_file() or sha(target)!=entry['sha256']:raise ValueError('Missing/changed restored build input: '+entry['path'])
            paths.add(entry['path'])
    native=project/'hardware/v1_2/native_projects/manifest.json'
    if native.exists():
        paths.add(str(native.relative_to(project)))
        for bundle in json.loads(native.read_text())['projects']:
            paths.add(bundle['archive'])
            for item in bundle['files']:
                if sha(project/item['path'])!=item['sha256']:raise ValueError('Changed native PCB input: '+item['path'])
                paths.add(item['path'])
    return {p:sha(project/p) for p in sorted(paths)}

def verify_resume(project, records, stages):
    project=Path(project);current=current_inputs(project);kept=[]
    build=json.loads((project/'mechanical/reports/build_manifest.json').read_text())
    for name,digest in build['input_sha256'].items():
        if current.get(name)!=digest:raise ValueError('Build inputs changed; resume from build: '+name)
    for stage in stages:
        rows=[row for row in records if row['stage']==stage and row['returncode']==0]
        if not rows:raise ValueError('No successful prior stage: '+stage)
        row=rows[-1]
        if row.get('input_sha256')!=current:raise ValueError('Missing/stale input evidence for '+stage+'; resume from build')
        artifacts=row.get('artifact_sha256',{})
        if not artifacts or any(not (project/p).is_file() or sha(project/p)!=h for p,h in artifacts.items()):raise ValueError('Missing/changed stage output: '+stage)
        kept.append(row)
    return kept

CORE_STAGES=('build','finalize_structure_metadata','validate','render','export','export_wheel_metal','delivery_check','report')

def save_pipeline_execution(project, records):
    """Publish the executed script/input/output fingerprints and exact stage logs."""
    project=Path(project);verify_resume(project,records,CORE_STAGES)
    payload={'commands.json':(json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode()}
    for row in records:
        name=row['log'];data=(project/'mechanical'/name).read_bytes()
        if row.get('log_sha256')!=hashlib.sha256(data).hexdigest():raise ValueError('Changed stage log: '+name)
        payload[name]=data
    target=project/'mechanical/reports/pipeline_execution.zip'
    fd,name=tempfile.mkstemp(prefix='.pipeline-',suffix='.zip',dir=target.parent);os.close(fd)
    try:
        with zipfile.ZipFile(name,'w',zipfile.ZIP_DEFLATED) as z:
            for path,data in payload.items():z.writestr(path,data)
        with zipfile.ZipFile(name) as z:
            if z.testzip() is not None:raise ValueError('Pipeline evidence ZIP failed CRC')
        os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)

def verify_pipeline_execution(project):
    project=Path(project)
    with zipfile.ZipFile(project/'mechanical/reports/pipeline_execution.zip') as z:
        records=json.loads(z.read('commands.json'))
        expected={'commands.json',*(row['log'] for row in records)}
        if set(z.namelist())!=expected or len(z.namelist())!=len(expected) or z.testzip() is not None:raise ValueError('Invalid pipeline evidence members')
        verify_resume(project,records,CORE_STAGES)
        for row in records:
            if row.get('returncode')!=0 or row.get('log_sha256')!=hashlib.sha256(z.read(row['log'])).hexdigest():raise ValueError('Failed/unverified pipeline stage: '+row['stage'])
    return records

def cad_python():
    configured=os.environ.get('MORI_CAD_PYTHON')
    binary=shutil.which(configured) if configured else sys.executable
    if not binary:raise RuntimeError('MORI_CAD_PYTHON does not resolve to an executable')
    result=subprocess.run([binary,'-c','from OCP.STEPControl import STEPControl_Writer'],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('CAD interpreter needs OCP (cadquery-ocp); set MORI_CAD_PYTHON to the environment documented in mechanical/README.md')
    return binary

def render_outputs(root, rows, expected, geometry):
    root=Path(root);by={row['view']:row for row in rows};errors=[]
    if len(by)!=len(rows):errors.append('Duplicate render view')
    for view in expected:
        if view not in by:errors.append('Missing render view: '+view)
    for view,row in by.items():
        path=root/'renders'/(view+'.png')
        if not path.is_file():errors.append('Missing render image: '+view);continue
        if row.get('geometry_sha256')!=geometry:errors.append('Stale render geometry: '+view)
        if row.get('image_sha256')!=sha(path) or row.get('image_bytes')!=path.stat().st_size:errors.append('Missing/stale image evidence: '+view)
    return {'status':'FAIL' if errors else 'PASS','expected_views':list(expected),'errors':errors}

def annotate_retries(commands, root):
    """A later zero exit alone is insufficient: log and produced evidence must match."""
    result=[]
    for row in commands:
        row=dict(row)
        if row.get('returncode'):
            retries=[r for r in commands if r['stage']==row['stage'] and r['started_utc']>row['started_utc'] and r.get('returncode')==0]
            verified=[]
            for retry in retries:
                outputs=retry.get('artifact_sha256',{})
                log=retry.get('log');digest=retry.get('log_sha256')
                if outputs and log and digest and (Path(root)/log).is_file() and sha(Path(root)/log)==digest and all((Path(root)/p).is_file() and sha(Path(root)/p)==h for p,h in outputs.items()):verified.append(retry)
            row['retry_verification']='PASS' if verified else 'BLOCKED'
            row['diagnostic']='Later successful retry with matching log and regenerated output hashes' if verified else 'Failure retained; a verified later retry and regenerated outputs are required'
            if verified:row['verified_retry_started_utc']=verified[-1]['started_utc']
        result.append(row)
    return result

EXPECTED_RENDER_VIEWS = ('electronics_bay', 'electronics_underside', 'pcb_power', 'pcb_motion', 'pcb_imu', 'pcb_rear', 'pcb_rear_bottom', 'pcb_bucks', 'bridge_joint_detail', 'bridge_joint_exploded', 'yaw_stop_detail', 'yaw_stop_exploded', 'battery_tray_fit', 'battery_frame_flat', 'battery_tray_wide', 'power_seats', 'power_board_mounted', 'battery_retention_detail', 'battery_retention_open', 'flush_bridge', 'flush_bridge_underside', 'flush_speaker', 'flush_cap', 'flush_reaction', 'consolidated_yaw', 'consolidated_base', 'consolidated_camera', 'consolidated_wheel', 'rear_interface_section', 'frame_underside', 'face_surface_side', 'imu_underside', 'rear_interface_detail', 'level_head_side', 'deck_plan', 'weact_detail', 'speaker_shell_detail', 'mic_detail', 'mic_open_path', 'belly_detail', 'yaw_drive_detail', '45_assembled', 'front', 'side', 'rear', 'top', 'bottom', 'exploded', 'internal', 'structure_only', 'structure_exploded', 'deck_detail', 'head_support', 'face_detail', 'head_section', 'screen_outline_review', 'clearance', 'balance_side', 'wheel_gap_detail', 'pose_up', 'pose_down', 'docked')
