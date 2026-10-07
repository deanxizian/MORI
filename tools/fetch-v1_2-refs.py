"""Fetch immutable refs; never reset or replace a user's existing checkout."""
import json,subprocess
from pathlib import Path
for ref in json.loads(Path('software/references_v1_2.lock.json').read_text())['repositories']:
    path=Path(ref['path'])
    if not path.exists():
        subprocess.run(['git','clone','--no-checkout','--filter=blob:none',ref['url'],str(path)],check=True)
        subprocess.run(['git','-C',str(path),'checkout','--detach',ref['commit']],check=True)
    actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if actual!=ref['commit']:raise SystemExit(f'{path}: local commit differs; preserved. Expected {ref["commit"]}')
    print(ref['name'],actual)
