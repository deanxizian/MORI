"""Inspect the exported transport file; never import or change a native board."""
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from prepare_freerouting import closing

b = Path('robot/.state/c3-completion/trials/R151-dsn-diagnostic')
out = b / 'constraint_audit.json'
assert not out.exists()
d = (b / 'R148E.dsn').read_text()
native = Path('robot/hardware/driver/development/native')
rule = (native / 'MORI_Interface_C3.kicad_dru').read_text()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((b / 'copy_manifest.json').read_text())
checks = []
for row in manifest['members']:
    src, copy = native / row['path'], b / 'native_copy' / row['path']
    checks.append(dict(path=row['path'], sha256=row['sha256'],
                       source_matches=sha(src) == row['sha256'],
                       copy_matches=sha(copy) == row['sha256']))
assert all(x['source_matches'] and x['copy_matches'] for x in checks)

counts = collections.Counter(re.findall(r'\(\s*([^\s()]+)', d))
layers = []
for m in re.finditer(r'(?m)^    \(layer\s', d):
    scope = d[m.start() + 4:closing(d, m.start() + 4) + 1]
    layers.append(dict(name=re.search(r'^\(layer\s+(\S+)', scope)[1],
                       type=re.search(r'\(type\s+(\S+)\)', scope)[1]))
keepouts = collections.Counter()
for m in re.finditer(r'\((keepout|wire_keepout|via_keepout)\s', d):
    scope = d[m.start():closing(d, m.start()) + 1]
    shape = re.search(r'\((polygon|rect|circle)\s+(\S+)', scope)
    if shape:
        keepouts[(m[1], shape[2])] += 1
r13 = rule[rule.index('(rule "R13 '):]
r13 = r13[:closing(r13, 0) + 1]
whitelist = re.findall(r"A\.NetName == '([^']+)'", r13)
assert len(layers) == 6 and all(x['type'] == 'signal' for x in layers)
assert counts['use_layer'] == 0
structure_start = d.index('(structure\n')
structure = d[structure_start:closing(d, structure_start) + 1]
inner_structure_keepouts = []
for m in re.finditer(r'\((keepout|wire_keepout)\s', structure):
    scope = structure[m.start():closing(structure, m.start()) + 1]
    shape = re.search(r'\(polygon\s+(In[14]\.Cu)\s+0\s+([^)]*)\)', scope)
    if shape:
        values = [float(x) for x in shape[2].split()]
        xs, ys = values[::2], values[1::2]
        bounds = [min(xs), min(ys), max(xs), max(ys)]
        assert not (bounds[0] <= 35000 <= bounds[2] and bounds[1] <= -17500 <= bounds[3])
        inner_structure_keepouts.append(dict(kind=m[1], layer=shape[1], bounds_um=bounds))

tool = Path('robot/.state/c3-completion/tools/freerouting')
java = tool / 'java-25.0.5/jdk-25.0.5+8-jre/Contents/Home/bin/java'
jar = tool / 'freerouting-2.5.0.jar'
download = next(x for x in json.loads((tool / 'downloads.json').read_text())
                if x['name'] == jar.name)
assert sha(jar) == download['sha256']
version = subprocess.run([str(java.absolute()), '-version'], capture_output=True, text=True)
assert version.returncode == 0
result = dict(
    scope=__doc__, dsn_sha256=sha(b / 'R148E.dsn'),
    source_board_sha256=sha(native / 'MORI_Interface_C3.kicad_pcb'),
    native_member_checks=checks, source_and_copy_unchanged=True,
    dsn_layers=layers,
    dsn_counts={k:counts[k] for k in ['keepout', 'wire_keepout', 'via_keepout', 'plane',
                                    'rule', 'class', 'use_layer', 'wire', 'via', 'padstack']},
    dsn_keepouts_by_layer=[dict(kind=k, layer=l, count=n)
                          for (k,l),n in sorted(keepouts.items())],
    native_rule_count=len(re.findall(r'^\(rule\s', rule, re.M)),
    native_r13_in2_allowed_nets=whitelist,
    inner_structure_keepouts=inner_structure_keepouts,
    findings=[
        'All six DSN layers are signal layers, with no use_layer restrictions. In1 structure keepouts cover only local mounting-hole regions; no board-wide In1/In4 track prohibition is exported. Native R13 therefore is not represented explicitly.',
        'DSN has three net classes and four generic rule scopes. It is not a complete transport of the native conditional rule set, including physical same-net via-pad and internal-zone requirements.',
        'Keepout geometry is present. Its semantic equivalence has not been newly qualified; the existing prepare_freerouting.py records guard-clearance and class-precedence transport corrections.',
        'The 23 plane polygons do not establish native refilled power continuity or retained reference-ground coverage.',
        'Do not use an unqualified DSN/SES round trip as a replacement board. Prior R118 evidence and incremental harvesting remain applicable.'
    ],
    local_runtime=dict(java=str(java), version_output=version.stderr or version.stdout,
                       jar=str(jar), jar_sha256=sha(jar),
                       installed_in_prior_work=True, new_installation=False,
                       note='MCP default dependency check searches a different JAR and PATH. Its not-ready result is not evidence that the project-local runtime is absent.'),
    autorouting_run=False, ses_import_run=False, native_save_run=False,
    manufacturing_release=False,
    next_step='If using multinet rerouting, explicitly translate R13 per-class allowed layers, preserve native guards, constrain selected net changes, and independently verify refill, old connections, power width, ground, and reference. Do not repeat the R118 unqualified full import.'
)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:result[k] for k in ['source_and_copy_unchanged', 'dsn_counts', 'native_rule_count', 'autorouting_run']}, ensure_ascii=False))
