#!/usr/bin/env python3
"""Write a current source + selected build artifact manifest under software/reports."""
import datetime,hashlib,json,pathlib,subprocess
SW=pathlib.Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={}
for p in sorted(SW.rglob('*')):
    relative=p.relative_to(SW)
    if p.is_file() and not any(part in {'reports','build','managed_components','__pycache__'} for part in relative.parts) and p.name!='sdkconfig.old':
        files[str(relative)]=sha(p)
artifacts={}
for name in ['firmware_work/firmware/build/mori_hardware_validation.elf','firmware_work/firmware/build/mori_hardware_validation.bin',
             'reports/compile_only/no_screen/mori_hardware_validation.bin',
             'reports/compile_only/DO_NOT_FLASH_gated_coverage/mori_hardware_validation.bin',
             'reports/hw04_baseline_build/mori_hardware_validation.elf',
             'reports/hw04_baseline_build/mori_hardware_validation.bin']:
    p=SW/name
    if p.exists():artifacts[name]=sha(p)
result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'handoff':'HW-SW-0.4','software':'SW-0.4',
        'git':{'status':'NOT_APPLICABLE','reason':'MORI workspace is not a Git repository'},
        'physical_validation':'NOT_TESTED','source_sha256':files,'artifact_sha256':artifacts}
path=SW/'reports/delivery_manifest.json';path.write_text(json.dumps(result,indent=2)+'\n')
print('PASS wrote',path,'sources=',len(files),'artifacts=',len(artifacts))
