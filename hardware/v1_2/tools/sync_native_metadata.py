#!/usr/bin/env python3
"""Refresh placement metadata from exact bundled PCBs; never alter PCB bytes."""
import argparse, hashlib, json, re, zipfile
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

def update(root=ROOT):
    manifest_path = root/'hardware/v1_2/native_projects/manifest.json'
    manifest = json.loads(manifest_path.read_text()); changes = []
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
        (root/meta).write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n')
        # Apply only tracked metadata updates inside the full project bundle.
        for name in content:
            if name.endswith(('/connectivity.json','/layout_notes.json','/rule_mapping.json')) and (root/name).exists(): content[name]=(root/name).read_bytes()
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for i in info: z.writestr(i, content[i.filename])
        project['bytes']=package.stat().st_size;project['sha256']=hashlib.sha256(package.read_bytes()).hexdigest()
        for row in project['files']:
            b=content[row['path']];row['bytes']=len(b);row['sha256']=hashlib.sha256(b).hexdigest()
        changes.append({'board':board,'pcb_sha256_unchanged':hashlib.sha256(content[board]).hexdigest(),'components':len(native)})
    manifest['metadata_revision']='2026-10-07 review correction; PCB/schematic/library bytes preserved from snapshot'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return changes
if __name__ == '__main__':
    print(json.dumps(update(),indent=2))
