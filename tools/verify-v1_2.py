"""V1.2 host checks. Embedded builds separately recorded; no device connection."""
import os,subprocess,sys
os.environ['MORI_REPORT_ROOT']='reports/v1_2'
checks=[('host_regression',[sys.executable,'tools/verify.py']),('motion_host_final',['bash','tools/test-motion-v1_2.sh']),('unitree_reference_final',['bash','tools/test-s288-reference.sh']),('eyes_360',['bash','tools/test-eyes-v1_2.sh'])]
fail=[]
for name,cmd in checks:
    if subprocess.run([sys.executable,'tools/record.py',name,'--',*cmd]).returncode:fail.append(name)
if fail:raise SystemExit('FAIL: '+', '.join(fail))
