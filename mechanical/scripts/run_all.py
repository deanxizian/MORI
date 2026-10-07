"""Portable pipeline runner, invoked with ordinary Python. Does not modify legacy A0 files."""
import sys,os,subprocess,json,datetime,shutil,argparse
from pathlib import Path
from pipeline_evidence import current_inputs, verify_resume, cad_python, sha, save_pipeline_execution
ROOT=Path(__file__).resolve().parents[1]
blender=os.environ.get('MORI_BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
parser=argparse.ArgumentParser();parser.add_argument('--core',action='store_true',help='Build/validate/render/export current outputs and refresh delivery/report; skip historical comparisons');parser.add_argument('--from-step',default='build',help='Resume at a named step, retaining successful preceding command records');parser.add_argument('--render-size',type=int,default=1200);parser.add_argument('--render-samples',type=int,default=32);args=parser.parse_args()
if args.render_size<64 or args.render_samples<1:parser.error('Render size must be >=64 and samples >=1')
master=ROOT/'mori_v1_2.blend'
steps=[('build',[str(master)] if master.exists() else []),('finalize_structure_metadata',[str(master)]),('validate',[str(master)]),('render',[str(master)]),('export',[str(master)])]
if not args.core:
    steps += [('check_integrated_stops',[str(ROOT/'mori_v1_2.blend')]),('check_rebuild',[str(ROOT/'mori_v1_2.blend')]),('body_head_envelope',[str(ROOT/'mori_v1_2.blend')]),('compare_variants',[]),('compare_structure',[]),('appearance_comparison',[]),('catalog',[str(ROOT/'mori_v1_2.blend')]),('review_s288_interfaces',[str(ROOT/'mori_v1_2.blend')])]
steps += [('export_wheel_metal',[]),('delivery_check',[str(master)]),('report',[])]
names=[name for name,_ in steps]
if args.from_step not in names:parser.error('--from-step must be one of '+', '.join(names))
start_at=names.index(args.from_step);records=[]
(ROOT/'reports').mkdir(parents=True,exist_ok=True)
if start_at:
    previous=json.loads((ROOT/'reports/commands.json').read_text())
    try:records=verify_resume(ROOT.parent,previous,names[:start_at])
    except (ValueError,OSError,KeyError) as error:parser.error(str(error))
    if start_at>names.index('validate') and json.loads((ROOT/'reports/validation.json').read_text())['counts']['FAIL']:parser.error('Cannot skip failed geometry validation; resume at validate instead')
steps=steps[start_at:]
for name,pre in steps:
    cmd=[blender,'--background','--python-exit-code','1',*pre,'--python',str(ROOT/'scripts'/(name+'.py'))]
    if name=='render':cmd += ['--','--size',str(args.render_size),'--samples',str(args.render_samples)]
    if name=='report':cmd=[sys.executable,str(ROOT/'scripts/report.py')]
    if name=='export_wheel_metal':cmd=[os.environ.get('MORI_CAD_PYTHON',sys.executable),str(ROOT/'scripts/export_wheel_metal.py')]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('RUN',name,flush=True)
    with (ROOT/'reports'/(name+'.log')).open('w') as log:
        try:
            if name!='build':verify_resume(ROOT.parent,records,[row['stage'] for row in records])
            if name=='export_wheel_metal':cmd[0]=cad_python()
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT.parent)
        except (OSError,ValueError,RuntimeError) as error:
            log.write(str(error)+'\n');result=subprocess.CompletedProcess(cmd,127)

    records.append({'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':result.returncode,'log':'reports/'+name+'.log'})
    if result.returncode==0:
        record=records[-1];record['input_sha256']=current_inputs(ROOT.parent)
        outputs=[ROOT/'mori_v1_2.blend',ROOT/'reports/build_manifest.json']
        if name=='validate':outputs.append(ROOT/'reports/validation.json')
        if name=='render':
            outputs.append(ROOT/'reports/render_manifest.json')
            outputs += [ROOT/'renders'/(r['view']+'.png') for r in json.loads(outputs[-1].read_text())]
        if name=='export':
            outputs.append(ROOT/'reports/export_manifest.json')
            outputs += [ROOT/r['file'] for r in json.loads(outputs[-1].read_text())['parts']]
        extra_reports={'export_wheel_metal':'wheel_metal_export','check_integrated_stops':'integrated_stop_check','check_rebuild':'rebuild_check','body_head_envelope':'body_head_envelope','compare_variants':'parameter_comparison','compare_structure':'structure_render_comparison','appearance_comparison':'appearance_comparison','catalog':'parts_preview_manifest','delivery_check':'delivery_consistency'}
        if name=='finalize_structure_metadata':outputs += [ROOT/'reports/structure_changes.json',ROOT/'reports/module_assembly.json']
        if name=='report':outputs += [ROOT/'reports/current_report.json',ROOT/'current_report.html']
        if name in extra_reports:outputs.append(ROOT/'reports'/(extra_reports[name]+'.json'))
        if name=='export_wheel_metal':outputs += [p for p in (ROOT/'metal_design').iterdir() if p.is_file()]
        if name=='review_s288_interfaces':outputs += [p for p in (ROOT/'studies/s288_interface_review').iterdir() if p.is_file()]
        record['artifact_sha256']={str(p.relative_to(ROOT.parent)):sha(p) for p in outputs}
        record['log_sha256']=sha(ROOT/record['log'])
    (ROOT/'reports/commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    if result.returncode:sys.exit(result.returncode)
    if name=='validate' and json.loads((ROOT/'reports/validation.json').read_text())['counts']['FAIL']:
        sys.exit('Geometry check failed; see validation.json. Outputs are not current approved candidates.')
    if name=='export':
        evidence=json.loads((ROOT/'reports/export_manifest.json').read_text())
        if evidence['candidate_count']!=evidence['exported_count']:sys.exit('Candidate STL export check failed; see export_manifest.json.')
save_pipeline_execution(ROOT.parent,records)
print('PIPELINE_COMPLETE: inspect reports/validation.json and export_manifest.json; NOT_TESTED/BLOCKED are explicit engineering limits.')
