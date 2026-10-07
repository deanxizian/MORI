#!/usr/bin/env python3
"""Refresh placement metadata from exact bundled PCBs; never alter PCB bytes."""
import fcntl, hashlib, io, json, os, re, shutil, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def sexpr(text):
    tokens = iter(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text))
    def nested():
        result = []
        for token in tokens:
            if token == ')': return result
            result.append(nested() if token == '(' else json.loads(token) if token.startswith('"') else token)
        raise ValueError('Unclosed KiCad expression')
    if next(tokens) != '(': raise ValueError('KiCad root expected')
    return nested()

def child(node, key, default=None):
    return next((v[1:] for v in node if isinstance(v, list) and v and v[0] == key), default)

def placements(data):
    result = {}
    for f in sexpr(data.decode()):
        if not isinstance(f, list) or not f or f[0] != 'footprint': continue
        props = {x[1]: x[2] for x in f if isinstance(x, list) and x[0] == 'property'}
        ref = props['Reference']; at = [float(v) for v in child(f, 'at')]
        if len(at) == 2: at.append(0.)
        result[ref] = dict(at=at, side=child(f, 'layer')[0].split('.')[0], footprint=f[1])
    return result

def atomic_bytes(path, data):
    fd, name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        Path(name).unlink(missing_ok=True)

def recover(root, transaction):
    journal=transaction/'journal.json'
    if journal.exists():
        for row in json.loads(journal.read_text()):
            relative=Path(row['path'])
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid recovery path')
            atomic_bytes(root/relative,(transaction/row['backup']).read_bytes())
    shutil.rmtree(transaction)

def publish(root, updates, transaction):
    """All data is validated before publication; interrupted writes recover next run."""
    transaction.mkdir();journal=[]
    try:
        for index,(path,data) in enumerate(updates.items()):
            atomic_bytes(transaction/f'new-{index}',data)
            atomic_bytes(transaction/f'old-{index}',path.read_bytes())
            journal.append({'path':str(path.relative_to(root)),'backup':f'old-{index}'})
        atomic_bytes(transaction/'journal.json',json.dumps(journal).encode())
        for index,path in enumerate(updates):atomic_bytes(path,(transaction/f'new-{index}').read_bytes())
        # Removing the journal commits the batch. Backups remain until every
        # archive, metadata file and the final manifest have reached disk.
        (transaction/'journal.json').unlink()
        fd=os.open(transaction,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    except BaseException:
        recover(root,transaction)
        raise
    else:shutil.rmtree(transaction)

def prepare_updates(root):
    manifest_path = root/'hardware/v1_2/native_projects/manifest.json'
    manifest = json.loads(manifest_path.read_text()); changes = [];updates={}
    for project in manifest['projects']:
        package = root/project['archive']
        with zipfile.ZipFile(package) as z:
            info = z.infolist(); content = {i.filename: z.read(i) for i in info}
        board = next(n for n in content if n.endswith('.kicad_pcb'))
        meta = next(n for n in content if n.endswith('/connectivity.json'))
        native = placements(content[board]); doc = json.loads((root/meta).read_text())
        for part in doc['components']:
            if part['ref'].startswith('#'):
                part['placement_scope']='SCHEMATIC_ONLY_NO_PCB_FOOTPRINT';continue
            p = native[part['ref']]
            part['at'] = p['at']; part['placed_at'] = p['at']; part['side'] = p['side']; part['footprint'] = p['footprint']
        doc['placement_provenance'] = {'source': board, 'sha256': hashlib.sha256(content[board]).hexdigest(), 'units': 'mm/degrees', 'coordinates': 'Native KiCad PCB coordinates, not assembly or sensor axes', 'generator': 'hardware/v1_2/tools/sync_native_metadata.py', 'physical_validation': 'NOT_TESTED'}
        doc['layout_revision'] = project['project'].rsplit('_', 1)[1]
        updates[root/meta]=(json.dumps(doc, ensure_ascii=False, indent=2)+'\n').encode()
        # Apply only tracked metadata updates inside the full project bundle.
        for name in content:
            if name.endswith(('/connectivity.json','/layout_notes.json','/rule_mapping.json')) and (root/name).exists(): content[name]=updates.get(root/name,(root/name).read_bytes())
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for i in info: z.writestr(i, content[i.filename])
        data=buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if z.testzip() is not None or any(z.read(n)!=b for n,b in content.items()):raise ValueError('Native ZIP verification failed')
        updates[package]=data
        project['bytes']=len(data);project['sha256']=hashlib.sha256(data).hexdigest()
        for row in project['files']:
            b=content[row['path']];row['bytes']=len(b);row['sha256']=hashlib.sha256(b).hexdigest()
        changes.append({'board':board,'pcb_sha256_unchanged':hashlib.sha256(content[board]).hexdigest(),'components':len(native)})
    manifest['metadata_revision']='2026-10-07 review correction; PCB/schematic/library bytes preserved from snapshot'
    updates[manifest_path]=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    return changes,updates

def update(root=ROOT):
    root=Path(root).resolve();state=root/'.state';state.mkdir(exist_ok=True)
    transaction=state/'native-metadata-transaction'
    with (state/'native-metadata.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if transaction.exists():recover(root,transaction)
        changes,updates=prepare_updates(root)
        if any(path.read_bytes()!=data for path,data in updates.items()):publish(root,updates,transaction)
    return changes
if __name__ == '__main__':
    print(json.dumps(update(),indent=2))
