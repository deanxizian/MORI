"""Read-only receipt of the hardware-owned, photo-backed FPC directions."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PACKAGE=ROOT/'hardware/v1_2/cam_fpc_exit_review_20261006'
OUT=HERE/'remaining_routes/static_flex/connector_faces'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
manifest=read(PACKAGE/'manifest.sha256.json')
assert manifest['revision']=='CAM-FPC-EXIT-R1'
assert manifest['file_count']==len(manifest['files'])
for file,h in manifest['files'].items():assert sha(PACKAGE/file)==h,file
hand=read(PACKAGE/'handoff.json');verify=read(PACKAGE/'results/verification.json')
assert hand['status']==verify['status']=='PASS'
assert hand['model_changes_applied'] is False
logical=hand['logical_map'];assert sha(ROOT/logical['source'])==logical['sha256']
protected=read(PACKAGE/'protected_baseline.json')['files']
for file,h in protected.items():assert sha(ROOT/file)==h,file
ports={r['model_reference']:r for r in hand['cam_ports']}
assert ports['CAMERA_FPC_24']['supported_exit_zero_pose_XYZ']==[0,0,1]
assert ports['DISPLAY_FPC_18']['supported_exit_zero_pose_XYZ']==[-1,0,0]
assert hand['lcd_endpoint']['supported_exit_zero_pose_XYZ']==[-1,0,0]
main=ROOT/'mechanical/mori_v1_2.blend'
assert sha(main)=='89cb07f571367bf87b627c771998d0cc0c28b873be575afdb4002c9bcf5b499f'
result=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='Evidence package hash receipt and nominal direction transfer only',
    revision=hand['revision'],source_package=str(PACKAGE.relative_to(ROOT)),
    manifest_sha256=sha(PACKAGE/'manifest.sha256.json'),
    handoff_sha256=sha(PACKAGE/'handoff.json'),
    package_files_checked=len(manifest['files']),protected_files_checked=len(protected),
    files={str((PACKAGE/f).relative_to(ROOT)):h for f,h in manifest['files'].items()},
    main_sha256=sha(main),main_changed=False,
    directions={k:dict(outward_zero_pose_XYZ=v['supported_exit_zero_pose_XYZ'],
        evidence=v['evidence'],photo_board_revision=v['photo_board_revision'],
        exact_mating='BLOCKED') for k,v in ports.items()},
    LCD_direction=hand['lcd_endpoint'],logical_map_unchanged=True,
    correction_scope='Camera-only package orientation candidate; DISPLAY entry must be separated from latch/body placement, not a whole-package flip.',
    physical_contact_faces='BLOCKED',full_cable_routes='BLOCKED',manufacturing_release=False,
    script_sha256=sha(Path(__file__)))
(OUT/'direction_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('FPC_DIRECTION_RECEIPT_DONE',result['status'],result['package_files_checked'])
