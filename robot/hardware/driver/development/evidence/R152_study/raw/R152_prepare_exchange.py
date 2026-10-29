"""Translate native R13 into a separate DSN proposal, preserving native inputs."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from prepare_freerouting import closing, prepare

b = Path('robot/.state/c3-completion/trials')
out = b / (sys.argv[1] if len(sys.argv) > 1 else 'R152-exchange')
assert not out.exists()
out.mkdir()
native = Path('robot/hardware/driver/development/native')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_sha = '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
assert sha(native / 'MORI_Interface_C3.kicad_pcb') == source_sha
raw = b / 'R151-dsn-diagnostic/R148E.dsn'
assert sha(raw) == json.loads((raw.parent / 'constraint_audit.json').read_text())['dsn_sha256']
adapted = out / 'guard-adapted.dsn'
prepare(raw, adapted)
text = adapted.read_text()
rules = (native / 'MORI_Interface_C3.kicad_dru').read_text()
r13 = rules[rules.index('(rule "R13 '):]
r13 = r13[:closing(r13, 0) + 1]
allowed_in2 = frozenset(re.findall(r"A\.NetName == '([^']+)'", r13))
assert len(allowed_in2) == 19
assert "A.Layer == 'In1.Cu' || A.Layer == 'In4.Cu'" in r13

# Keep layer numbering and through-via spans. These two layers are not route
# layers in the native project; class rules below independently express R13.
for layer in ['In1.Cu', 'In4.Cu']:
    old = '(layer ' + layer + '\n      (type signal)'
    assert text.count(old) == 1
    text = text.replace(old, '(layer ' + layer + '\n      (type power)', 1)

classes = []
seen = set()
for m in reversed(list(re.finditer(r'(?m)^    \(class\s', text))):
    start = m.start() + 4
    end = closing(text, start)
    scope = text[start:end + 1]
    circuit_at = scope.index('\n      (circuit')
    head = re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+', scope[:circuit_at])
    assert head[0] == 'class'
    original_class = head[1]
    nets = [json.loads(t) if t.startswith('"') else t for t in head[2:]]
    assert not seen.intersection(nets)
    seen.update(nets)
    width = re.findall(r'\(width\s+([\d.]+)\)', scope)
    via = re.findall(r'\(use_via\s+("(?:\\.|[^"\\])*"|[^\s()]+)\)', scope)
    assert len(width) == len(via) == 1
    replacements = []
    for in2 in [False, True]:
        members = sorted(n for n in nets if (n in allowed_in2) == in2)
        if not members:
            continue
        name = original_class + ('_In2' if in2 else '')
        layers = ['F.Cu'] + (['In2.Cu'] if in2 else []) + ['In3.Cu', 'B.Cu']
        c = '(class ' + name + '\n      ' + '\n      '.join(json.dumps(n) for n in members)
        c += '\n      (circuit (use_via ' + via[0] + ') (use_layer ' + ' '.join(layers) + '))'
        c += '\n      (rule (width ' + width[0] + '))\n    )'
        replacements.append(c)
        classes.append(dict(name=name, source_class=original_class, nets=members,
                            layers=layers, width_um=float(width[0]), via=via[0]))
    text = text[:start] + '\n    '.join(replacements) + text[end + 1:]

# This run uses explicit layer activity, not a guess based on overlapping
# exported plane outlines. R13 still filters In2 separately for each class.
settings = '\n    (autoroute_settings\n      (fanout off)\n      (autoroute on)\n      (postroute off)'
for layer, active, direction in [('F.Cu', True, 'horizontal'), ('In1.Cu', False, 'vertical'),
                                  ('In2.Cu', True, 'vertical'), ('In3.Cu', True, 'horizontal'),
                                  ('In4.Cu', False, 'vertical'), ('B.Cu', True, 'vertical')]:
    settings += '\n      (layer_rule ' + layer + ' (active ' + ('on' if active else 'off') + ') (preferred_direction ' + direction + '))'
settings += '\n    )\n  '
# Freerouting 2.5.0's Structure parser only consumes autoroute_settings while
# layerStructure is null. A prior plane initializes it; placing this block
# after planes then silently truncates board reading. Put it before boundary
# and planes, after the six layer declarations. Confirm full inventory on load.
start = text.index('(structure\n')
insert_at = text.index('    (boundary\n', start)
assert insert_at < text.index('    (plane ', start)
text = text[:insert_at] + settings + text[insert_at:]
target = out / 'R148E-r13.dsn'
target.write_text(text)
assert sum(len(x['nets']) for x in classes) == len(seen)
assert {n for x in classes if 'In2.Cu' in x['layers'] for n in x['nets']} == allowed_in2
assert '(type route)' not in text
record = dict(scope=__doc__, source_board_sha256=source_sha, source_dsn_sha256=sha(raw),
              output_dsn_sha256=sha(target), classes=sorted(classes, key=lambda x:x['name']),
              native_r13_sha256=hashlib.sha256(r13.encode()).hexdigest(),
              native_in2_nets=sorted(allowed_in2),
              source_native_unchanged=sha(native / 'MORI_Interface_C3.kicad_pcb') == source_sha,
              parser_order_guard='autoroute_settings precedes planes; loaded component/pin/net counts must still be checked',
              existing_copper='All exported source wires and vias protected for the first constrained proposal.',
              limits=['This translates R13 only, plus previously established guard transport semantics.',
                      'Conditional native clearances, physical same-net via-pad spacing, actual zone topology, reference ground and component-body review still require independent native checks.',
                      'No imported board is an accepted candidate. No manufacturing or physical qualification.'])
(out / 'translation.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'classes':len(classes), 'nets':len(seen), 'in2_allowed':len(allowed_in2),
                  'dsn_sha256':sha(target), 'native_unchanged':record['source_native_unchanged']}))
