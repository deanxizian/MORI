#!/usr/bin/env python3
"""Record an exact argv, cwd, UTC times, exit code and log SHA256. No shell."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True)
    p.add_argument('--cwd', type=pathlib.Path, default=ROOT.parent)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd or not a.name.replace('_', '').replace('-', '').isalnum():
        p.error('command and simple unique name required')
    directory = ROOT / 'reports' / a.name
    directory.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if path.is_file() and not any(part in {'reports','build','managed_components','__pycache__'} for part in relative.parts):
            inputs[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = dict(argv=cmd, cwd=str(a.cwd.resolve()), start_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  evidence_type='SIMULATED' if a.name.startswith('SIMULATED') else 'HOST_BUILD_OR_STATIC', inputs_sha256=inputs)
    with (directory / 'output.log').open('wb') as log:
        try:
            result = subprocess.run(cmd, cwd=a.cwd, stdout=log, stderr=subprocess.STDOUT, check=False)
            code = result.returncode
        except OSError as e:
            log.write(str(e).encode()); code = 127
    record.update(end_utc=dt.datetime.now(dt.timezone.utc).isoformat(), exit_code=code,
                  status='PASS' if code == 0 else 'FAIL',
                  log_sha256=hashlib.sha256((directory / 'output.log').read_bytes()).hexdigest())
    (directory / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k:v for k,v in record.items() if k != 'inputs_sha256'}, indent=2))
    print((directory / 'output.log').read_text(errors='replace')[-6000:])
    return code

if __name__ == '__main__':
    sys.exit(main())
