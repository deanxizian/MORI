"""Execute and record the native-electronics delivery, resumable after a failure."""
from pathlib import Path
import sys,subprocess,json,datetime,argparse
from concurrent.futures import ThreadPoolExecutor
P=Path(__file__).resolve().parents[2];R=P/'mechanical';B='/Applications/Blender.app/Contents/MacOS/Blender';K='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3';C='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'
master=R/'mori_v1_2.blend';records=[]
def blender(script,extra=(),source=master):return [B,'--background',str(source),'--python-exit-code','1','--python',str(R/'scripts'/f'{script}.py'),*(['--',*extra] if extra else [])]
ids='Body_IMU,Body_Upper,Head_Buck,Head_Buck_Insert_0,Head_Buck_Insert_1,Head_Buck_Screw_0,Head_Buck_Screw_1,Load_Frame,MCU_Carrier,Power_Module,Power_Switch,Rear_Interface_Insert_0,Rear_Interface_Insert_1,Rear_Interface_PCB,Rear_Interface_Screw_0,Rear_Interface_Screw_1,USB_Receptacle,Wheel_Buck,Wheel_Buck_Insert_1,Wheel_Buck_Insert_2,Wheel_Buck_Screw_1,Wheel_Buck_Screw_2'
groups=[
 [('native_export',[K,str(R/'scripts/prepare_populated_pcbs.py'),'export'])],
 [('native_convert',[C,str(R/'scripts/convert_populated_pcbs.py')])],
 [('native_supplement',[C,str(R/'scripts/supplement_populated_pcbs.py')])],
 [('build',blender('build'))],
 [('validate',blender('validate'))],
 [('render',blender('render',['--views','all','--size','1000','--samples','20'])),('export',blender('export')),('export_wheel_metal',[C,str(R/'scripts/export_wheel_metal.py')])],
 [('check_rebuild',blender('check_rebuild'))],
 [('catalog',blender('catalog',['--ids',ids])),('export_electronics_detail',blender('export_electronics_detail')),('assembly_animation',blender('assembly_animation',['--width','960','--samples','16','--render','stills']))],
 [('check_animation',blender('check_assembly_animation',['--native-only'],R/'mori_assembly_animation.blend')),('delivery_check',blender('delivery_check')),('check_electronics_detail',blender('check_electronics_detail',source=R/'mori_electronics_detail.blend'))],
 [('report',[sys.executable,str(R/'scripts/report.py')])]]
def run(row):
    name,cmd=row;start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('RUN',name,flush=True)
    with (R/'reports'/f'{name}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=P)
    record={'stage':name,'command':cmd,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':r.returncode,'log':'reports/'+name+'.log'}
    print('DONE',name,r.returncode,flush=True);return record
parser=argparse.ArgumentParser();parser.add_argument('--from-stage',default='native_export');parser.add_argument('--validate-after-rebuild',action='store_true');a=parser.parse_args()
if a.validate_after_rebuild:
    groups.insert(next(i for i,g in enumerate(groups) if g[0][0]=='check_rebuild')+1,[('validate_post_metadata',blender('validate'))])
names=[g[0][0] for g in groups];i=names.index(a.from_stage)
if i:
    old=json.loads((R/'reports/commands.json').read_text());keep={n for g in groups[:i] for n,c in g};records=[r for r in old if r['stage'] in keep]
for group in groups[i:]:
    with ThreadPoolExecutor(max_workers=len(group)) as pool:new=list(pool.map(run,group))
    records+=new;(R/'reports/commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    if any(r['returncode'] for r in new):sys.exit('Stage failed; inspect recorded logs')
    if any(r['stage'].startswith('validate') for r in new) and json.loads((R/'reports/validation.json').read_text())['counts']['FAIL']:sys.exit('Geometry FAIL; do not publish')
print('NATIVE_DELIVERY_COMPLETE',flush=True)
