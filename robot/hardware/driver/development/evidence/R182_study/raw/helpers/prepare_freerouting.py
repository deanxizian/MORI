"""Prepare an isolated DSN routing proposal without changing native KiCad rules.

KiCad keepout polygons are already exclusion boundaries. Freerouting otherwise
adds the default copper clearance to them. An explicit zero-offset guard class
preserves those boundaries. Redundant 200-um per-net-class clearances are removed
from this DSN only: in Freerouting they replace the item classes and defeat the
separate SMD clearance. Source native DRC remains authoritative.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def closing(text, start):
    depth = 0
    quoted = escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if escaped:
            escaped = False
        elif char == '\\' and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return i
    raise ValueError('Unbalanced DSN scope')


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    original = source.read_text()
    text = original
    ends = [closing(text, m.start()) for m in re.finditer(r'\((?:keepout|via_keepout|wire_keepout)\s', text)]
    for end in reversed(ends):
        text = text[:end] + ' (clearance_class kicadguard)' + text[end:]
    assert text.count('(rule\n      (width 200)\n      (clearance 200)') == 1
    extra = '\n      (clearance 200 (type wire_smd))'
    for kind in ['wire', 'via', 'smd', 'pin', 'area', 'kicadguard']:
        extra += '\n      (clearance 0 (type ' + kind + '_kicadguard))'
    text = text.replace('(clearance 50 (type smd_smd))', '(clearance 50 (type smd_smd))' + extra, 1)
    removed = 0
    for match in reversed(list(re.finditer(r'(?m)^    \(class\s', text))):
        start = match.start() + 4
        end = closing(text, start)
        scope = text[start:end + 1]
        count = scope.count('(clearance 200)')
        assert count == 1, 'Expected one unqualified 200-um class clearance'
        scope = scope.replace('(clearance 200)', '')
        text = text[:start] + scope + text[end + 1:]
        removed += count
    protected = text.count('(type route)')
    text = text.replace('(type route)', '(type protect)')
    destination.write_text(text)
    receipt = {'source': str(source), 'output': str(destination),
               'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
               'guard_scopes': len(ends), 'redundant_class_clearances_removed': removed,
               'protected_wire_and_via_paths': protected,
               'limits': ['Only DSN transport semantics are adjusted; native files are not saved.',
                          'Native conditional rules, via flash-layer details, filled power continuity and reference planes still require native validation.',
                          'SES imports can alter existing geometry or padstack behaviour; harvest incremental proposals and preserve original board items.']}
    destination.with_suffix('.preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('destination')
    args = p.parse_args(); prepare(args.source, args.destination)
