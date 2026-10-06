"""Portable pipeline runner, invoked with ordinary Python. Does not modify legacy A0 files."""
import sys,os,subprocess,json,datetime,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
blender=os.environ.get('MORI_BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
parser=argparse.ArgumentParser();parser.add_argument('--core',action='store_true',help='Only build/validate/render/export; skip gallery and supplementary checks');args=parser.parse_args()
steps=[('build',[]),('validate',[str(ROOT/'mori_v1_2.blend')]),('render',[str(ROOT/'mori_v1_2.blend')]),('export',[str(ROOT/'mori_v1_2.blend')])]
if not args.core:
    steps += [('check_rebuild',[str(ROOT/'mori_v1_2.blend')]),('body_head_envelope',[str(ROOT/'mori_v1_2.blend')]),('servo_orientation_study',[str(ROOT/'mori_v1_2.blend')]),('compare_variants',[]),('compare_structure',[]),('appearance_comparison',[]),('catalog',[str(ROOT/'mori_v1_2.blend')]),('delivery_check',[str(ROOT/'mori_v1_2.blend')])]
records=[]
for name,pre in steps:
    cmd=[blender,'--background','--python-exit-code','1',*pre,'--python',str(ROOT/'scripts'/(name+'.py'))]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('RUN',name,flush=True)
    with (ROOT/'reports'/(name+'.log')).open('w') as log: result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT.parent)
    records.append({'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':result.returncode,'log':'reports/'+name+'.log'})
    (ROOT/'reports/commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    if result.returncode:sys.exit(result.returncode)
    if name=='validate' and json.loads((ROOT/'reports/validation.json').read_text())['counts']['FAIL']:
        sys.exit('Geometry check failed; see validation.json. Outputs are not current approved candidates.')
    if name=='export':
        evidence=json.loads((ROOT/'reports/export_manifest.json').read_text())
        if evidence['candidate_count']!=evidence['exported_count']:sys.exit('Candidate STL export check failed; see export_manifest.json.')
if not args.core:
    cmd=[sys.executable,str(ROOT/'scripts/report.py')];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (ROOT/'reports/report.log').open('w') as log: result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT.parent)
    records.append({'stage':'report','command':cmd,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':result.returncode,'log':'reports/report.log'})
    (ROOT/'reports/commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    if result.returncode:sys.exit(result.returncode)
print('PIPELINE_COMPLETE: inspect reports/validation.json and export_manifest.json; NOT_TESTED/BLOCKED are explicit engineering limits.')
