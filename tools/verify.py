"""Current software checks; hardware checks deliberately excluded."""
import subprocess,sys
commands=[('contracts_generate',[sys.executable,'contracts/generate.py']),('typescript',['bash','tools/node-env.sh','test']),('python',[sys.executable,'-m','pytest','simulation/tests','backend/tests','-q']),('native',['bash','tools/test-native.sh']),('legacy_host',['bash','software/scripts/test_host.sh']),('legacy_python',[sys.executable,'-m','unittest','discover','-s','software/tests','-p','test_*.py']),('web_build',['bash','tools/node-env.sh','build'])]
failed=[]
for name,cmd in commands:
 r=subprocess.run([sys.executable,'tools/record.py',name,'--',*cmd])
 if r.returncode:failed.append(name)
if failed:raise SystemExit('FAIL: '+','.join(failed))
