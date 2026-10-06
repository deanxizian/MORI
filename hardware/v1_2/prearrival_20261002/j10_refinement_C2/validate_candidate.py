"""Read-only audit of the C2 placement study, never a PCB release test.

Run with KiCad's bundled Python. Writes only this study's audit files.
"""
import collections
import hashlib
import json
from pathlib import Path

import pcbnew as k
import wx

app = wx.App(False)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NAME = 'MORI_power_J10_C2_CANDIDATE'
DIR = HERE / NAME
PCB = DIR / (NAME + '.kicad_pcb')
A2 = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A2.json'
A2_SHA = 'b7ee51734472dd4a4cab364447354422f3af690250e0d9349caa64c2842945b9'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def xy(p):
    return [round(k.ToMM(p.x), 6), round(k.ToMM(p.y), 6)]


def snapshot(path):
    board = k.LoadBoard(str(path))
    footprints = {}
    for f in board.GetFootprints():
        footprints[f.GetReference()] = dict(
            xy_mm=xy(f.GetPosition()),
            angle_deg=round(f.GetOrientationDegrees(), 6),
            side=board.GetLayerName(f.GetLayer()),
            value=f.GetValue(),
            library=str(f.GetFPID().GetLibNickname()) + ':' + str(f.GetFPID().GetLibItemName()),
            pads=sorted([dict(number=p.GetNumber(), xy_mm=xy(p.GetPosition()),
                             net=p.GetNetname(), size_mm=xy(p.GetSize()),
                             drill_mm=xy(p.GetDrillSize())) for p in f.Pads()],
                        key=lambda p: p['number']),
        )
    edges = sorted([dict(shape=int(s.GetShape()), start=xy(s.GetStart()), end=xy(s.GetEnd()))
                    for s in board.GetDrawings() if s.GetLayer() == k.Edge_Cuts],
                   key=lambda s: str(s))
    return dict(footprints=footprints, edges=edges,
                copper_layers=board.GetCopperLayerCount(),
                tracks_and_vias=len(list(board.GetTracks())))


def numbered(f):
    return [(p['number'], p['xy_mm'], p['net']) for p in f['pads']]


def run():
    a2 = read(A2)
    formal = a2['native_source_manifest']
    source_checks = {p: sha(ROOT / p) == h for p, h in formal.items()}
    old = snapshot(ROOT / 'hardware/v1_2/kicad/MORI_power_P5R6/MORI_power_P5R6.kicad_pcb')
    new = snapshot(PCB)
    changed = {r: dict(before=old['footprints'][r], after=f)
               for r, f in new['footprints'].items() if f != old['footprints'][r]}
    expected = {'J10', 'D30', 'F70', 'R50', 'JP70', 'TP71'}
    drc = read(HERE / 'reports/FINAL_PLACEMENT_ONLY_drc.json')
    cmd = read(HERE / 'reports/FINAL_PLACEMENT_ONLY_command.json')
    erc = read(HERE / 'reports/FINAL_erc.json')
    ecmd = read(HERE / 'reports/FINAL_erc_command.json')
    project = read(DIR / (NAME + '.kicad_pro'))
    settings = project['board']['design_settings']
    old_settings = read(ROOT / 'hardware/v1_2/kicad/MORI_power_P5R6/MORI_power_P5R6.kicad_pro')['board']['design_settings']
    erc_violations = [v for sheet in erc['sheets'] for v in sheet['violations']]
    report_hashes = {str(p.relative_to(ROOT)): sha(p) for p in [PCB, DIR / (NAME + '.kicad_sch'),
                     DIR / (NAME + '.kicad_pro'), DIR / (NAME + '.kicad_dru'),
                     HERE / 'reports/FINAL_PLACEMENT_ONLY_drc.json', HERE / 'reports/FINAL_erc.json']}
    findings = {
        'formal_native_sources_unchanged': all(source_checks.values()),
        'received_A2_unchanged': sha(A2) == A2_SHA,
        'only_listed_footprints_changed': set(changed) == expected,
        'same_footprint_set': set(old['footprints']) == set(new['footprints']),
        'outline_unchanged': old['edges'] == new['edges'],
        'copper_layer_count_unchanged': old['copper_layers'] == new['copper_layers'],
        'J10_numbered_holes_and_nets_unchanged': numbered(old['footprints']['J10']) == numbered(new['footprints']['J10']),
        'J10_candidate_holes_0p90_lands_1p50': all(p['drill_mm'] == [.9, .9] and p['size_mm'] == [1.5, 1.5]
                                                for p in new['footprints']['J10']['pads']),
        'backside_parts_numbered_pads_unchanged': all(numbered(old['footprints'][r]) == numbered(new['footprints'][r])
                                                     and new['footprints'][r]['side'] == 'B.Cu' for r in ['D30', 'F70', 'R50']),
        'no_new_DRC_exclusions': settings.get('drc_exclusions', []) == old_settings.get('drc_exclusions', []) == [],
        'rule_severities_unchanged': settings.get('rule_severities') == old_settings.get('rule_severities'),
        'DRC_matches_current_board_hash': cmd['pcb_sha256'] == sha(PCB),
        'schematic_parity_zero': len(drc['schematic_parity']) == 0,
        'ERC_zero': not erc_violations and ecmd['returncode'] == 0,
        'no_manufacturing_export_in_candidate': not any(p.suffix.lower() in ['.gbr', '.drl', '.gbrjob'] for p in HERE.rglob('*')),
    }
    result = dict(
        id='J10_C2_A3_INTEGRITY_AUDIT',
        integrity_status='PASS' if all(findings.values()) else 'FAIL',
        scope='Source preservation, candidate interfaces and accurate reporting only; NOT a routed-board acceptance test.',
        design_status='BLOCKED', manufacturing_release=False, physical_tests='NOT_TESTED',
        checks=findings, source_checks=source_checks, changed_footprints=changed,
        reports=dict(kicad_version=drc['kicad_version'], ERC_violations=len(erc_violations),
                     DRC_status='FAIL', DRC_exit_code=cmd['returncode'],
                     DRC_violations=len(drc['violations']),
                     DRC_types=dict(collections.Counter(v['type'] for v in drc['violations'])),
                     DRC_severities=dict(collections.Counter(v['severity'] for v in drc['violations'])),
                     unconnected_items=len(drc['unconnected_items']), schematic_parity=len(drc['schematic_parity'])),
        hashes=report_hashes,
    )
    (HERE / 'candidate_snapshot.json').write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'integrity_status': result['integrity_status'], 'checks': findings,
                      'reports': result['reports']}, ensure_ascii=False, indent=2))
    assert all(findings.values()), 'Candidate interface/source audit failed; inspect validation.json.'


if __name__ == '__main__':
    run()
