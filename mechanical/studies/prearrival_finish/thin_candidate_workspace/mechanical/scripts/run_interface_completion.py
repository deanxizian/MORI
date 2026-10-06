"""Record current M1.43 regeneration, checks and presentation synchronization.

This publishes candidate geometry only, never a manufacturing release. The
separate digital review records pending design decisions and known open issues.
"""
import argparse,datetime,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; B='/Applications/Blender.app/Contents/MacOS/Blender'
steps=['build','check_rebuild','validate','render','export','export_wheel_metal','finalize_structure_metadata','catalog','export_electronics_detail','check_electronics_detail','delivery_check']
parser=argparse.ArgumentParser();parser.add_argument('--from-step',choices=steps,default=steps[0]);args=parser.parse_args()
records=json.loads((R/'reports/interface_commands.json').read_text()) if args.from_step!=steps[0] else []
steps=steps[steps.index(args.from_step):]
for stage in steps:
    cmd=[B,'-b',str(R/'mori_v1_2.blend'),'--python-exit-code','1','--python',str(R/'scripts'/f'{stage}.py')]
    if stage=='check_electronics_detail':cmd[2]=str(R/'mori_electronics_detail.blend')
    if stage=='export_wheel_metal':cmd=['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python',str(R/'scripts/export_wheel_metal.py')]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('INTERFACE_RUN',stage,flush=True)
    log=R/'reports'/f'interface_{stage}.log'
    with log.open('w') as stream:result=subprocess.run(cmd,cwd=R.parent,stdout=stream,stderr=subprocess.STDOUT)
    records.append({'stage':stage,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':result.returncode,'log':str(log.relative_to(R))})
    (R/'reports/interface_commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
    if stage=='validate' and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:raise SystemExit('Current implemented-geometry checks failed; inspect report.')
    if stage=='check_rebuild' and json.loads((R/'reports/rebuild_check.json').read_text())['status']!='PASS':raise SystemExit('Rebuild not deterministic.')
print('INTERFACE_ARTIFACTS_COMPLETE',flush=True)
