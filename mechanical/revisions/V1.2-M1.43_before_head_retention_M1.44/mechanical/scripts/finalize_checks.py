"""Record actual supplementary execution commands and finalize deterministic build evidence."""
import sys,subprocess,datetime,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];exe='/Applications/Blender.app/Contents/MacOS/Blender';records=[]
steps=[('check_rebuild',[]),('body_head_envelope',[]),('catalog',['--','--ids','Head_Front,USB_Receptacle'])]
for name,args in steps:
 cmd=[exe,'--background','--python-exit-code','1',str(root/'mori_v1_2.blend'),'--python',str(root/'scripts'/(name+'.py')),*args]
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (root/'reports'/(name+'_final.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 records.append({'stage':name,'command':cmd,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':r.returncode})
 (root/'reports/additional_commands.json').write_text(json.dumps(records,indent=2))
 if r.returncode:sys.exit(r.returncode)
print('FINAL_CHECKS_COMPLETE')
