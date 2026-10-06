"""Read-only receipt of routed C3; preserve original A3 geometry evidence."""
from pathlib import Path
import json, hashlib, datetime, sys, os
import pcbnew as k
import wx
app = wx.App(False)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
hp = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A6_J10_C3.json'
h = read(hp)
ap = ROOT / h['base_placement_handoff']
assert sha(ap) == h['base_placement_handoff_sha256']
a = read(ap)
bp = ROOT / h['candidate']['pcb']
sp = ROOT / h['candidate']['schematic']
assert sha(bp) == h['candidate']['pcb_sha256']
assert sha(sp) == h['candidate']['schematic_sha256']
sources = {str(p.relative_to(ROOT)): sha(p) for p in [hp, ap, bp, sp]}
for path, digest in {**a['native_source_manifest'], **a['candidate']['hashes']}.items():
    assert sha(ROOT / path) == digest, path
    sources[path] = digest

def xy(v): return [v.x, v.y]
def vec(v): return [v.x, v.y, v.z]
def model(m):
    return dict(file=str(m.m_Filename), scale=vec(m.m_Scale),
                offset=vec(m.m_Offset), rotation=vec(m.m_Rotation))
def geometry(board):
    result = {}
    for fp in board.GetFootprints():
        pads = [dict(number=p.GetNumber(), xy=xy(p.GetPosition()),
            angle=p.GetOrientationDegrees(), size=xy(p.GetSize()),
            drill=xy(p.GetDrillSize()), shape=int(p.GetShape()),
            attribute=int(p.GetAttribute()), layers=p.GetLayerSet().FmtHex(),
            net=p.GetNetname()) for p in fp.Pads()]
        result[fp.GetReference()] = dict(xy=xy(fp.GetPosition()),
            angle=fp.GetOrientationDegrees(), layer=fp.GetLayer(),
            value=fp.GetValue(), models=[model(m) for m in fp.Models()],
            pads=sorted(pads, key=lambda p: (p['number'], p['xy'])))
    return result
def outline(board):
    result = []
    for edge in board.GetDrawings():
        if edge.GetLayer() != k.Edge_Cuts: continue
        result.append(dict(shape=int(edge.GetShape()), start=xy(edge.GetStart()),
            end=xy(edge.GetEnd()), width=edge.GetWidth(),
            middle=xy(edge.GetArcMid()) if edge.GetShape() == k.SHAPE_T_ARC else None))
    return sorted(result, key=lambda row: json.dumps(row, sort_keys=True))

old_path = ROOT / a['candidate']['board']
old = k.LoadBoard(str(old_path)); new = k.LoadBoard(str(bp))
g0, g1 = geometry(old), geometry(new)
changes = [ref for ref in set(g0) | set(g1) if g0.get(ref) != g1.get(ref)]
assert not changes, changes
assert len(g1) == 112
assert sum(len(v['pads']) for v in g1.values()) == 280
assert outline(old) == outline(new)
assert old.GetDesignSettings().GetBoardThickness() == new.GetDesignSettings().GetBoardThickness() == 1600000
assert old.GetCopperLayerCount() == new.GetCopperLayerCount() == 4

# Confirm that identical model strings resolve to identical local model data.
model_checks = []
for ref, row in g1.items():
    for m in row['models']:
        name = m['file']
        p0 = Path(os.path.expandvars(name.replace('${KIPRJMOD}', str(old_path.parent))))
        p1 = Path(os.path.expandvars(name.replace('${KIPRJMOD}', str(bp.parent))))
        if not p0.is_absolute(): p0 = old_path.parent / p0
        if not p1.is_absolute(): p1 = bp.parent / p1
        assert p0.is_file() == p1.is_file(), (ref, name, p0, p1)
        if not p0.is_file():
            model_checks.append(dict(reference=ref, model=name, status='BLOCKED',
                reason='The identical original library model reference is unresolved on both sources; no physical dimension claim.',
                before_resolved_file=str(p0), after_resolved_file=str(p1)))
            continue
        assert sha(p0) == sha(p1), (ref, name)
        model_checks.append(dict(reference=ref, model=name, status='PASS', sha256=sha(p1)))

rd = bp.parents[1] / 'reports'
received = {}
for kind, source, key in [('drc', bp, 'pcb_sha256'), ('erc', sp, 'schematic_sha256')]:
    cmdp = rd / ('FINAL_command.json' if kind == 'drc' else 'FINAL_erc_command.json')
    rp = rd / ('FINAL_' + kind + '.json')
    cmd, report = read(cmdp), read(rp)
    assert cmd['returncode'] == 0 and cmd[key] == sha(source)
    if kind == 'drc':
        assert not report['violations'] and not report['unconnected_items'] and not report['schematic_parity']
    else:
        assert report['sheets'] and not any(s.get('violations') for s in report['sheets'])
    received[kind] = dict(status='PASS', input_sha256=sha(source), command=str(cmdp.relative_to(ROOT)), report=str(rp.relative_to(ROOT)))
    sources[str(cmdp.relative_to(ROOT))] = sha(cmdp); sources[str(rp.relative_to(ROOT))] = sha(rp)

review = HERE / 'J10_A3_review/review.json'
out = dict(status='PASS', scope='Independent native mechanical equality and received electrical report integrity only',
    verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    kicad_python_version=k.Version(), python=sys.version, sources=sources,
    footprint_count=len(g1), numbered_pad_count=280, footprint_differences=changes,
    model_file_checks=model_checks, outline_and_thickness_unchanged=True,
    received_electrical_checks=received, geometry_basis_review=str(review.relative_to(ROOT)),
    geometry_basis_sha256=sha(review), retained_geometry_scope='Body/backside envelopes, bare plug swept boxes and limited tool allocations only',
    main_sha256=sha(ROOT / 'mechanical/mori_v1_2.blend'), main_geometry_changed=False,
    formal_boards_replaced=False, candidate_adopted=False, manufacturing_release=False,
    remaining=h['remaining_mechanical_items'],
    limits=['No electrical qualification was independently repeated by mechanics.',
        'Equality of references and actual model files does not certify original vendor or photo dimensions.',
        'Historical A3 nearest-normal wire-screen failures are not inherited as proof that a route is impossible.',
        'A3 tool and bare housing sweeps do not qualify an attached cable, a selected gripping tool or full assembly.',
        'PHC1 remains a separate unmerged candidate; all formal PCB sources stay read-only.'])
(HERE / 'hardware_A6_J10_C3_receipt.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print('A6_MECHANICAL_RECEIPT_PASS', len(g1), 'footprints', len(model_checks), 'model files')
