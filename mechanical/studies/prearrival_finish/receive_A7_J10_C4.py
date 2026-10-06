"""Read-only mechanical receipt of C4 and head-interface evidence; no adoption."""
from pathlib import Path
import ast, collections, csv, datetime, hashlib, json, os, sys
import pcbnew as k
import wx
app = wx.App(False)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sources = {}

def source(p, expected=None):
    p = Path(p)
    digest = sha(p)
    if expected is not None:
        assert digest == expected, str(p)
    sources[str(p.relative_to(ROOT))] = digest
    return read(p) if p.suffix == '.json' else p

# Reuse only pure readers from the historical receipt, never its top-level writes.
helpers = HERE / 'receive_A6_J10_C3.py'
source(helpers)
tree = ast.parse(helpers.read_text())
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
assert {n.name for n in functions} == {'xy', 'vec', 'model', 'geometry', 'outline'}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(helpers), 'exec'))

hp = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A7_J10_C4_head_harness.json'
h = source(hp)
a = source(ROOT / h['base_handoff'], h['base_handoff_sha256'])
bp, sp = (ROOT / h['candidate'][key] for key in ['pcb', 'schematic'])
source(bp, h['candidate']['pcb_sha256'])
source(sp, h['candidate']['schematic_sha256'])
old_path = ROOT / a['candidate']['pcb']
source(old_path, a['candidate']['pcb_sha256'])
old, new = k.LoadBoard(str(old_path)), k.LoadBoard(str(bp))
g0, g1 = geometry(old), geometry(new)
changes = [ref for ref in set(g0) | set(g1) if g0.get(ref) != g1.get(ref)]
assert not changes, changes
assert len(g1) == 112 and sum(len(v['pads']) for v in g1.values()) == 280
assert outline(old) == outline(new)
assert old.GetDesignSettings().GetBoardThickness() == new.GetDesignSettings().GetBoardThickness() == 1600000
assert old.GetCopperLayerCount() == new.GetCopperLayerCount() == 4

def vias(board):
    rows = [dict(xy=xy(t.GetPosition()), diameter_by_layer=[t.GetWidth(layer) for layer in [k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]], drill=t.GetDrillValue(),
                 net=t.GetNetname(), kind=int(t.GetViaType()), layers=t.GetLayerSet().FmtHex())
            for t in board.GetTracks() if isinstance(t, k.PCB_VIA)]
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
assert vias(old) == vias(new) and len(vias(new)) == 147

model_checks = []
for ref, row in g1.items():
    for m in row['models']:
        paths = []
        for board_path in [old_path, bp]:
            p = Path(os.path.expandvars(m['file'].replace('${KIPRJMOD}', str(board_path.parent))))
            paths.append(p if p.is_absolute() else board_path.parent / p)
        p0, p1 = paths
        assert p0.is_file() == p1.is_file(), (ref, paths)
        result = dict(reference=ref, model=m['file'], resolved_path=str(p1))
        if p1.is_file():
            assert sha(p0) == sha(p1), ref
            result.update(status='PASS', sha256=sha(p1))
        else:
            result.update(status='BLOCKED', reason='Same original model missing in both local sources; no complete component fit claim.')
        model_checks.append(result)
assert len(model_checks) == 100

rd = bp.parents[1] / 'reports'
received = {}
for kind, input_file, key in [('drc', bp, 'pcb_sha256'), ('erc', sp, 'schematic_sha256')]:
    cp = rd / ('FINAL_command.json' if kind == 'drc' else 'FINAL_erc_command.json')
    rp = rd / ('FINAL_' + kind + '.json')
    command, report = source(cp), source(rp)
    assert command['returncode'] == 0 and command[key] == sha(input_file)
    if kind == 'drc':
        assert all(not report[field] for field in ['violations', 'unconnected_items', 'schematic_parity', 'ignored_checks'])
    else:
        assert report['sheets'] and not any(s.get('violations') for s in report['sheets'])
    received[kind] = dict(status='PASS', source_sha256=sha(input_file),
                         report=str(rp.relative_to(ROOT)), independently_rerun=False)

manifest_checks = []
for mp, wrapped in [
    (ROOT / 'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json', False),
    (rd / 'C3_input_hashes.json', False),
    (rd.parent / 'delivery_manifest.json', True),
    (ROOT / 'hardware/v1_2/head_harness_evidence_20261003/delivery_manifest.json', True)]:
    doc = source(mp)
    mapping = doc['files'] if wrapped else doc
    for name, digest in mapping.items():
        assert sha(ROOT / name) == digest, name
    manifest_checks.append(dict(path=str(mp.relative_to(ROOT)), file_count=len(mapping), status='PASS'))

vr = source(ROOT / h['checks']['visual_records'])
assert vr['before_sha256'] == sha(old_path) and vr['after_sha256'] == sha(bp)
def rows(path):
    source(path)
    with path.open(newline='') as f: return list(csv.DictReader(f))
flags = rows(rd.parent / '39_flag_dispositions.csv')
counts = dict(collections.Counter(row['decision'] for row in flags))
assert len(flags) == 39 and counts == h['checks']['flag_dispositions'] == vr['dispositions']
assert all(row['reason'] and row['record_status'] == 'PASS' for row in flags)
escapes = rows(rd.parent / '70_own_escape_dispositions.csv')
coverage = rows(rd.parent / '104_component_coverage.csv')
assert len(escapes) == 70 and len(coverage) == 104
assert all(row['specific_reason'] for row in escapes)
for row in flags:
    for key in ['before_image', 'after_image']:
        if row[key] == 'UNCHANGED_NATIVE_GEOMETRY':
            assert row['decision'] != 'FIXED'
        elif row[key]:
            assert (rd.parent / row[key]).is_file(), row[key]
load = source(rd / 'load_path_audit.json')
assert load['status'] == 'PASS' and load['pcb_sha256'] == sha(bp) and len(load['rows']) == 27

ep = ROOT / h['head_harness']['evidence']
e = source(ep, h['head_harness']['evidence_sha256'])
pins = rows(ROOT / h['head_harness']['pinmap'])
assert len(pins) == 37
assert all(row['physical_cavity_view'] == 'BLOCKED' for row in pins)
retrievals = source(ep.parent / 'sources_manifest.json')
successful = []
for row in retrievals:
    if row['status'] == 'PASS':
        source(ep.parent / 'sources' / row['file'], row['sha256'])
        successful.append(row['file'])
cached = e['feetech_reuse']
source(ROOT / cached['path'], cached['sha256'])
source(ep.parent / cached['cached_file'], cached['sha256'])
for row in h['head_harness']['mechanical_receipt']:
    source(ROOT / row['source'], row['sha256'])
    source(ROOT / row['snapshot'], row['sha256'])

main = ROOT / 'mechanical/mori_v1_2.blend'
source(main, 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f')
out = dict(status='PASS', scope='Independent native mechanical equality and received-file integrity; not an electrical or complete-harness qualification',
    verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    kicad_python_version=k.Version(), python=sys.version, sources=sources,
    footprint_count=112, numbered_pad_count=280, via_count=147,
    footprint_differences=changes, outline_thickness_layers_unchanged=True,
    via_geometry_and_nets_unchanged=True, model_file_checks=model_checks,
    manifest_checks=manifest_checks, received_electrical_checks=received,
    received_visual_review=dict(status='PASS', scope=vr['scope'], flags=39,
        dispositions=counts, own_escape_rows=70, component_coverage=104,
        independently_repeated=False, user_aesthetic_approval='NOT_TESTED'),
    head_evidence=dict(status='PASS', pinmap_rows=37, primary_downloads_verified=successful,
        cached_feetech_verified=True, actual_connector_cavity_views='BLOCKED',
        complete_harness='BLOCKED', current_sample_SH_direct_crimp='FAIL',
        explanation='SH SSH-003T-P0.2-H accepts insulation OD0.4–0.8mm; Alpha5853 catalogue sample is0.889–1.0922mm. A smaller factory tail/transition or selected compatible conductor is still required.'),
    mechanical_basis='mechanical/studies/prearrival_finish/J10_A3_review/review.json',
    main_sha256=sha(main), main_geometry_changed=False, formal_boards_replaced=False,
    C4_adopted=False, PHC1_merged=False, manufacturing_release=False,
    remaining=h['remaining_mechanical_items'] + h['head_harness']['primary_missing'],
    limits=['Received ERC/DRC and visual records are hardware-owner results, not independently repeated electrical tests.',
        'No physical mating dimensions are inferred from schematic pin numbers or candidate connector catalogues.',
        'Original ten missing model references remain unresolved; realistic reference envelopes are not vendor CAD.',
        'A3 bare-plug sweeps do not validate terminal tails, actual grip access or final harness assembly.'])
(HERE / 'hardware_A7_J10_C4_receipt.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print('A7_MECHANICAL_RECEIPT_PASS',112,'footprints',280,'pads',147,'vias',counts)
