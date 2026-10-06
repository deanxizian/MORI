#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only closure of the P5R6 and R08/R09/R39 external reviews.

Run with KiCad's bundled Python. No production CAD, contracts or manufacturing
outputs are changed. The rule test deliberately alters a disposable copy and
requires the expected native DRC failures; that copy is never a design revision.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pcbnew as k

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1_2'
OUT = H / 'reviews/P5R6_and_width_external_20260925'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
RULES = Path('/Users/dean/Documents/KiCad/Rules/pcb-rules.json')
REVISIONS = dict(power='P5R6', motion='P5R6', rear='P5R6', imu='P5R4')
NATIVE_SUFFIXES = {'.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_dru',
                   '.kicad_mod', '.kicad_sym'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def load(p):
    return json.loads(p.read_text())


def paths(kind):
    name = 'MORI_' + kind + '_' + REVISIONS[kind]
    directory = H / 'kicad' / name
    return name, directory, directory / (name + '.kicad_pcb')


def inputs(directory):
    return {str(f.relative_to(ROOT)): sha(f) for f in sorted(directory.rglob('*'))
            if f.is_file() and (f.suffix in NATIVE_SUFFIXES or
                               f.name in ['fp-lib-table', 'sym-lib-table'])}


def xy(point):
    return round(k.ToMM(point.x), 6), round(k.ToMM(point.y), 6)


def point(x, y):
    return k.VECTOR2I(k.FromMM(x), k.FromMM(y))


def pad(board, ref, pin):
    return next(p for f in board.GetFootprints() if f.GetReference() == ref
                for p in f.Pads() if p.GetNumber() == str(pin))


def track_row(board, track):
    return dict(uuid=track.m_Uuid.AsString(), net=track.GetNetname(),
                layer=board.GetLayerName(track.GetLayer()),
                start_mm=xy(track.GetStart()), end_mm=xy(track.GetEnd()),
                width_mm=round(k.ToMM(track.GetWidth()), 6),
                length_mm=round(k.ToMM(track.GetLength()), 6))


def native_rules(directory, name):
    text = (directory / (name + '.kicad_dru')).read_text()
    blocks = {}
    for rule_id in ['R08', 'R09', 'R39']:
        m = re.search(r'\(rule "(' + rule_id + r' [^"]+)"\s*(.*?)\n\)', text, re.S)
        assert m, rule_id
        block = m.group(0)
        condition = re.search(r'\(condition "([^"]*)"\)', block)
        width = re.search(r'\(constraint track_width \(min ([0-9.]+)mm\) '
                          r'\(opt ([0-9.]+)mm\) \(max ([0-9.]+)mm\)\)', block)
        assert width, block
        blocks[rule_id] = dict(name=m.group(1), condition=condition.group(1) if condition else None,
                               min_mm=float(width.group(1)), opt_mm=float(width.group(2)),
                               max_mm=float(width.group(3)), file_offset=m.start(), text=block)
    assert blocks['R09']['file_offset'] < blocks['R08']['file_offset'] < blocks['R39']['file_offset']
    assert blocks['R09']['condition'] is None
    assert blocks['R39']['condition'] == "A.inDiffPair('*')"
    # R08 currently contains only OR-ed exact net tests. Do not pretend to be a
    # general KiCad expression evaluator if a later project changes that syntax.
    condition = blocks['R08']['condition']
    assert not re.sub(r"A.NetName == '[^']+'|0 == 1|\|\||[()\s]", '', condition)
    blocks['R08']['net_membership'] = re.findall(r"A.NetName == '([^']+)'", condition)
    return blocks


def inventory():
    source_path = RULES if RULES.is_file() else OUT / 'evidence/source_rules_full.json'
    source_rules = load(source_path)
    selected = [r for r in source_rules['rules'] if r['id'] in ['R08', 'R09', 'R39']]
    dump(OUT / 'evidence/source_rules_R08_R09_R39.json',
         dict(path=str(source_path), original_path=str(RULES), sha256=sha(source_path), rules=selected))
    manifest = load(OUT / 'external/evidence/summary.json')
    result, rows, boards = {}, [], {}
    for kind in REVISIONS:
        name, directory, pcb = paths(kind)
        assert sha(pcb) == manifest[kind]['sha256_pcb']
        assert sha(directory / (name + '.kicad_sch')) == manifest[kind]['sha256_sch']
        b = k.LoadBoard(str(pcb)); boards[kind] = b
        rules = native_rules(directory, name)
        tracks = [t for t in b.GetTracks() if not isinstance(t, k.PCB_VIA)]
        assert not any(isinstance(t, k.PCB_ARC) for t in tracks), 'Update arc path handling before use'
        names = {t.GetNetname() for t in tracks}
        paired = {n for n in names if n.endswith(('_P', '_N')) and
                  n[:-1] + ('N' if n[-1] == 'P' else 'P') in names}
        assert paired == ({'/KELVIN_P', '/KELVIN_N'} if kind == 'power' else set())
        histogram = Counter()
        for t in tracks:
            row = dict(board=name, **track_row(b, t))
            rule = 'R39' if row['net'] in paired else (
                'R08' if row['net'] in rules['R08']['net_membership'] else 'R09')
            row.update(width_rule=rule, permitted_min_mm=rules[rule]['min_mm'],
                       preferred_mm=rules[rule]['opt_mm'], permitted_max_mm=rules[rule]['max_mm'])
            row['status'] = 'PASS' if row['permitted_min_mm']-1e-7 <= row['width_mm'] <= row['permitted_max_mm']+1e-7 else 'FAIL'
            assert row['status'] == 'PASS', row
            histogram[row['width_mm']] += 1
            rows.append(row)
        result[kind] = dict(board=name, pcb_sha256=sha(pcb),
                            schematic_sha256=manifest[kind]['sha256_sch'],
                            width_histogram_mm=dict(sorted(histogram.items())),
                            segments=len(tracks), arcs=0, minimum_mm=min(histogram), maximum_mm=max(histogram),
                            rules=rules, paired_nets=sorted(paired),
                            scope='Explicit track widths only; no thermal or plane-neck qualification', status='PASS')
    assert len(rows) == 1502
    with (OUT / 'all_1502_segments.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    dump(OUT / 'evidence/width_inventory.json', result)
    return boards, result


def path_distance(b, net, start_pad, end_pad, include_pad_centres=False):
    """Planar endpoint graph; not copper edge length or electrical loop area."""
    tracks = [t for t in b.GetTracks() if not isinstance(t, k.PCB_VIA) and t.GetNetname() == net]
    vias = [v for v in b.GetTracks() if isinstance(v, k.PCB_VIA) and v.GetNetname() == net]
    key = lambda p, layer: (*xy(p), layer)
    nodes = {key(p, t.GetLayer()) for t in tracks for p in [t.GetStart(), t.GetEnd()]}
    nodes.update(key(v.GetPosition(), layer) for v in vias for layer in [k.F_Cu, k.B_Cu])
    graph = {q: [] for q in nodes}
    def edge(a, z, length):
        graph.setdefault(a, []).append((z, length)); graph.setdefault(z, []).append((a, length))
    for t in tracks:
        a, z = xy(t.GetStart()), xy(t.GetEnd())
        length2 = sum((v-u)**2 for u, v in zip(a, z))
        points = []
        for node in nodes:
            if node[2] != t.GetLayer(): continue
            f = sum((v-u)*(q-u) for u, v, q in zip(a, z, node[:2])) / length2
            nearest = tuple(u+f*(v-u) for u, v in zip(a, z))
            if -1e-7 <= f <= 1+1e-7 and math.dist(nearest, node[:2]) < 2e-6:
                points.append((f, node))
        points.sort()
        for (_, u), (_, v) in zip(points, points[1:]): edge(u, v, math.dist(u[:2], v[:2]))
    for v in vias: edge(key(v.GetPosition(), k.F_Cu), key(v.GetPosition(), k.B_Cu), 0)
    for label, pp in [('start', start_pad), ('end', end_pad)]:
        graph[label] = []
        for node in nodes:
            if pp.IsOnLayer(node[2]) and pp.HitTest(point(*node[:2])):
                edge(label, node, math.dist(xy(pp.GetPosition()), node[:2]) if include_pad_centres else 0)
        assert graph[label], (net, label)
    costs = {'start': 0}; queue = [(0, 0, 'start')]; sequence = 0
    while queue:
        cost, _, node = heapq.heappop(queue)
        if cost != costs[node]: continue
        if node == 'end': return cost
        for target, length in graph[node]:
            value = cost + length
            if value < costs.get(target, float('inf')):
                costs[target] = value; sequence += 1
                heapq.heappush(queue, (value, sequence, target))
    raise AssertionError(('no path', net))


def kelvin_and_boot(b):
    sections = [
        ('positive upstream sense', '/BAT_REV', ('R2', 1), ('R3', 1), .2,
         [(30.0375, 13.35), (30.0375, 14.6), (29.175, 15.4625), (29.175, 16.5)]),
        ('negative upstream sense', '/BAT_MON', ('R2', 2), ('R4', 1), .2,
         [(36.45, 13.35), (38, 14.9), (38, 15.675)]),
        ('positive named differential', '/KELVIN_P', ('R3', 2), ('U1', 3), .381,
         [(30.825, 16.5), (31.05, 16.5), (31.55, 17), (31.55, 18.95), (32.05, 19.45), (32.8625, 19.45)]),
        ('negative named differential', '/KELVIN_N', ('R4', 2), ('U1', 4), .381,
         [(38, 17.325), (38, 18.95), (37.5, 19.45), (35.1375, 19.45)]),
    ]
    data = []
    for label, net, src, dst, width, coords in sections:
        # KiCad import can differ from displayed coordinates by 1 nm. Retain
        # actual coordinates/UUIDs in evidence; this tolerance only locates them.
        located = lambda p: any(math.dist(xy(p), q) < 2e-6 for q in coords)
        ts = [t for t in b.GetTracks() if not isinstance(t, k.PCB_VIA) and t.GetNetname() == net and
              located(t.GetStart()) and located(t.GetEnd())]
        assert len(ts) == (3 if label.startswith('positive upstream') else 2 if label.startswith('negative upstream') else 4 if 'positive named' in label else 3)
        assert all(abs(k.ToMM(t.GetWidth())-width) < 1e-7 for t in ts)
        # Verify this exact subset connects the two pads; no whole power-net detour.
        remaining = set(range(len(ts))); seen = set()
        queue = [i for i, t in enumerate(ts) if t.GetEffectiveShape(k.F_Cu).Collide(pad(b, *src).GetEffectiveShape(k.F_Cu), 0)]
        while queue:
            i = queue.pop()
            if i in seen: continue
            seen.add(i); remaining.discard(i)
            queue += [j for j in remaining if ts[i].GetEffectiveShape(k.F_Cu).Collide(ts[j].GetEffectiveShape(k.F_Cu), 0)]
        assert len(seen) == len(ts)
        assert any(ts[i].GetEffectiveShape(k.F_Cu).Collide(pad(b, *dst).GetEffectiveShape(k.F_Cu), 0) for i in seen)
        data.append(dict(section=label, net=net, source='.'.join(map(str, src)), destination='.'.join(map(str, dst)),
                         width_mm=width, applied_width_rule='R39' if 'named' in label else 'R08',
                         trace_length_mm=sum(k.ToMM(t.GetLength()) for t in ts),
                         status='PASS', segments=[track_row(b, t) for t in ts]))
    dump(OUT / 'evidence/kelvin_complete_sense_paths.json',
         dict(status='PASS', pcb_sha256=sha(paths('power')[2]), sections=data,
              scope='R39 matches named /KELVIN_P and /KELVIN_N, not the entire functional sense path across R3/R4.',
              intent='The 5 upstream 0.20mm tap tracks are explicitly checked, not omitted or treated as load-current trunks.',
              physical_noise_offset='NOT_TESTED'))
    lengths = []
    for number, prefix in [(60, 'M5'), (70, 'C5')]:
        row = dict(IC=f'U{number}')
        for definition, include in [('track_endpoint_metric', False), ('including_pad_centre_links', True)]:
            values = {suffix: path_distance(b, '/'+prefix+'_'+suffix, pad(b, f'U{number}', pin), pad(b, f'C{number+2}', cp), include)
                      for suffix, pin, cp in [('BOOT', 6, 1), ('SW', 2, 2)]}
            values['sum_mm'] = sum(values.values()); row[definition] = values
        lengths.append(row)
    assert abs(lengths[1]['including_pad_centre_links']['BOOT']-2.625) < 2e-6
    assert abs(lengths[1]['track_endpoint_metric']['BOOT']-2.45) < 2e-6
    dump(OUT / 'evidence/bootstrap_length_definitions.json',
         dict(pcb_sha256=sha(paths('power')[2]), status='PASS', channels=lengths,
              definition='Endpoint metric counts complete native segments on the path. It does NOT clip segments at pad edges. Entry-to-pad-centre links are optional; via barrels and internal device paths are excluded in both cases.',
              C5_difference_mm=.175, physical_loop_inductance='NOT_TESTED'))


def check(kind):
    name, directory, pcb = paths(kind)
    report_dir = OUT / 'native' / kind; report_dir.mkdir(parents=True, exist_ok=True)
    before = inputs(directory); log = []
    commands = [
        [CLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors', '--schematic-parity',
         '--refill-zones', '--exit-code-violations', '-o', str(report_dir / 'drc.json'), str(pcb)],
        [CLI, 'sch', 'erc', '--format', 'json', '--severity-all', '--exit-code-violations',
         '-o', str(report_dir / 'erc.json'), str(directory / (name + '.kicad_sch'))],
    ]
    for args in commands:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=300)
        log.append(dict(utc=datetime.now(timezone.utc).isoformat(), argv=args, returncode=cp.returncode,
                        stdout=cp.stdout, stderr=cp.stderr))
    dump(report_dir / 'commands.json', dict(input_sha256=before, commands=log))
    assert before == inputs(directory), ('native check changed inputs', kind)
    assert all(c['returncode'] == 0 for c in log), log
    drc, erc = load(report_dir / 'drc.json'), load(report_dir / 'erc.json')
    erc_count = sum(len(s.get('violations', [])) for s in erc.get('sheets', []))
    result = dict(status='PASS', ERC=erc_count, DRC=len(drc['violations']),
                  unconnected=len(drc['unconnected_items']), parity=len(drc['schematic_parity']),
                  pcb_sha256=sha(pcb), source_inputs_unchanged=True)
    assert result['ERC'] == result['DRC'] == result['unconnected'] == result['parity'] == 0
    pro = load(directory / (name + '.kicad_pro'))
    result['DRC_exclusions'] = pro['board']['design_settings']['drc_exclusions']
    result['ignored_DRC_checks'] = [n for n, v in pro['board']['design_settings']['rule_severities'].items() if v == 'ignore']
    result['ignored_ERC_checks'] = [n for n, v in pro['erc']['rule_severities'].items() if v == 'ignore']
    assert not result['DRC_exclusions'] and not result['ignored_DRC_checks'] and not result['ignored_ERC_checks']
    print(kind, 'native ERC/DRC/parity/unconnected = 0', flush=True)
    return kind, result


def rule_probe():
    """Expected-failure check of R08/R09/R39 in a disposable full project."""
    name, directory, pcb = paths('power')
    probes = [('/ARM_Q', .15, 'R09 signal width'), ('/FAULT_N', 2.1, 'R09 signal width'),
              ('/BAT_REV', .15, 'R08 power and return width'), ('/H6_IN', 5.1, 'R08 power and return width'),
              ('/KELVIN_P', .3, 'R39 differential geometry'), ('/KELVIN_N', .4, 'R39 differential geometry')]
    evidence = OUT / 'rule_probe'; evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='MORI_RULE_PROBE_NOT_A_DESIGN_') as temp:
        td = Path(temp) / name
        shutil.copytree(directory, td, ignore=shutil.ignore_patterns('*.kicad_prl', '*.lck'))
        tp = td / pcb.name; b = k.LoadBoard(str(tp)); mutations = []
        for net, width, rule in probes:
            ts = [t for t in b.GetTracks() if not isinstance(t, k.PCB_VIA) and t.GetNetname() == net]
            t = min(ts, key=lambda item: item.m_Uuid.AsString())
            if net == '/BAT_REV':
                t = next(t for t in ts if {xy(t.GetStart()), xy(t.GetEnd())} == {(30.0375, 13.35), (30.0375, 14.6)})
            mutations.append(dict(uuid=t.m_Uuid.AsString(), net=net, original_mm=k.ToMM(t.GetWidth()),
                                  probe_mm=width, expected_native_rule=rule))
            t.SetWidth(k.FromMM(width))
        k.SaveBoard(str(tp), b)
        args = [CLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors',
                '--exit-code-violations', '-o', str(evidence / 'expected_failures_drc.json'), str(tp)]
        cp = subprocess.run(args, capture_output=True, text=True, timeout=300)
        report = load(evidence / 'expected_failures_drc.json')
        assert cp.returncode != 0, 'The deliberately invalid widths must fail native DRC'
        for probe in mutations:
            matches = [v for v in report['violations'] if v['type'] == 'track_width' and
                       any(item.get('uuid') == probe['uuid'] for item in v['items'])]
            assert matches and any(probe['expected_native_rule'] in v['description'] for v in matches), (probe, matches)
            probe['native_findings'] = matches; probe['expected_rule_detected'] = True
        dump(evidence / 'probe_result.json', dict(status='PASS',
             scope='Expected failure proves width-rule matching and precedence for these six specific segments only. This is NOT the current board DRC result.',
             current_board_unchanged=True, current_pcb_sha256=sha(pcb), temporary_probe_sha256=sha(tp),
             temporary_copy_deleted_after_test=True, commands=[dict(argv=args, returncode=cp.returncode,
             stdout=cp.stdout, stderr=cp.stderr)], probes=mutations))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', action='store_true', help='Fresh ERC/DRC on the four immutable native projects')
    parser.add_argument('--probe', action='store_true', help='Expected-failure width-rule check in a disposable copy')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    before = {kind: inputs(paths(kind)[1]) for kind in REVISIONS}
    boards, inventory_result = inventory()
    kelvin_and_boot(boards['power'])
    # Reuse existing high-resolution native geometry evidence only after
    # confirming it describes these exact byte-identical source files.
    geometry_sources = {}
    for fname in ['buck_returns.json', 'load_path_audit.json', 'bootstrap_and_SW_banks.json']:
        src = H / 'layout_P5R6/reports/power' / fname
        d = load(src); assert d['pcb_sha256'] == sha(paths('power')[2]) and d['status'] == 'PASS'
        geometry_sources[fname] = dict(path=str(src.relative_to(ROOT)), sha256=sha(src),
                                      pcb_sha256=d['pcb_sha256'], evidence_reused=True)
    dump(OUT / 'evidence/reused_geometry_evidence.json', geometry_sources)
    native = None
    if args.native:
        with ThreadPoolExecutor(max_workers=2) as executor:
            native = dict(executor.map(check, REVISIONS))
    if args.probe:
        rule_probe()
    assert before == {kind: inputs(paths(kind)[1]) for kind in REVISIONS}
    dump(OUT / 'verification.json', dict(
        utc=datetime.now(timezone.utc).isoformat(),
        tool=subprocess.check_output([CLI, '--version'], text=True).strip(),
        source_inputs=before, source_inputs_unchanged=True, schematic_and_copper_changes=0,
        board_revision='P5R6 motion/power/rear, P5R4 IMU', reviewed_segments=1502,
        width_values='PASS', full_Kelvin_functional_route_inventory='PASS',
        native=native, native_rule_probe='PASS' if args.probe else 'NOT_TESTED',
        full_source_rule_equivalence='NOT_TESTED', thermal_ampacity='NOT_TESTED',
        manufacturing_release='BLOCKED', mechanical_and_firmware_changed=False,
        retained_exceptions=['R13 two dedicated In1.Cu feedback ground returns',
                             'Rear CC2 strict R14 bevel FAIL', 'IMU short GND escape style exceptions']))
    print('P5R6 review closure: 1502 track widths checked; all native sources unchanged', flush=True)


if __name__ == '__main__':
    main()
