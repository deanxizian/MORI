"""Run a bounded, local Freerouting DSN readback or routing proposal."""
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
mode = sys.argv[1]
assert mode in ('readback', 'route')
out = b / (sys.argv[2] if len(sys.argv) > 2 else 'R152-' + mode)
assert not out.exists()
out.mkdir()
original = b / 'R152-exchange/R148E-r13.dsn'
data = original.read_text()
if mode == 'readback':
    assert data.count('(autoroute on)') == 1
    data = data.replace('(autoroute on)', '(autoroute off)')
input_file = out / 'input.dsn'
input_file.write_text(data)
userdata = out / 'user-data'
userdata.mkdir()
enabled = mode == 'route'
settings = dict(version='2.5.0', gui=dict(enabled=False),
                user_profile=dict(user_id=str(uuid.uuid4()), disable_analytics=True),
                api_server=dict(enabled=False), mcp_server=dict(enabled=False),
                router=dict(autorouter=dict(enabled=enabled, max_passes=4),
                            fanout=dict(enabled=False), optimizer=dict(enabled=False)),
                logging=dict(file=dict(enabled=True)))
(userdata / 'freerouting.json').write_text(json.dumps(settings, indent=2) + '\n')
tool = Path('robot/.state/c3-completion/tools/freerouting')
java = tool / 'java-25.0.5/jdk-25.0.5+8-jre/Contents/Home/bin/java'
jar = tool / 'freerouting-2.5.0.jar'
output = out / ('result.dsn' if mode == 'readback' else 'result.ses')
cmd = [str(java.absolute()), '-Xmx4g', '-Djava.awt.headless=true', '-jar', str(jar.absolute()),
       '-de', str(input_file.absolute()), '-do', str(output.absolute()), '-da',
       '--router.autorouter.max_passes=4', '--router.optimizer.max_threads=0',
       '--user_data_path=' + str(userdata.absolute()), '--gui.enabled=false',
       '--api_server.enabled=false', '--mcp_server.enabled=false',
       '--router.autorouter.enabled=' + str(enabled).lower(),
       '--router.fanout.enabled=false', '--router.optimizer.enabled=false',
       '--router.job_timeout=00:02:00', '--router.result_json=' + str((out / 'result.json').absolute())]
record = dict(scope=__doc__, mode=mode, argv=cmd,
              input_sha256=hashlib.sha256(input_file.read_bytes()).hexdigest(),
              output=str(output), new_installation=False)
receipt = out / 'command.json'
(out / 'runner_source.py').write_bytes(Path(__file__).read_bytes())
receipt.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(mode=mode, started=True, command_record=str(receipt))), flush=True)
t = time.time()
with (out / 'console.log').open('w') as log:
    try:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        record['returncode'] = proc.returncode
    except subprocess.TimeoutExpired:
        record.update(returncode=None, outer_timeout_seconds=180, process_terminated=True)
record['elapsed_seconds'] = time.time() - t
record['output_exists'] = output.exists()
if output.exists():
    record['output_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
receipt.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k:record[k] for k in ['mode', 'returncode', 'elapsed_seconds', 'output_exists']}), flush=True)
