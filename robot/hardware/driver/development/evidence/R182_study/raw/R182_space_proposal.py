"""Build an unadopted 70 x 40 mm space model, never a routing/fit certificate.

The original 70 x 35 mm board is immutable. Power/reference zones are not
extended; the extra strip is intentionally unpowered and unrouted.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper, pcb, uid, xy, via_snapshot, polyset

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source = dev / 'native'
dest = b / 'R182I'
board_name = 'MORI_Interface_C3.kicad_pcb'
expected_sha = '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_members = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
assert source_members[board_name] == expected_sha
assert not dest.exists()
py = str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
commands = []

def write(name, value):
    with (b / name).open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')

def run(step, argv, allowed=(0,)):
    started = time.time()
    r = subprocess.run(argv, text=True, capture_output=True)
    commands.append(dict(step=step, argv=argv, returncode=r.returncode,
                         stdout=r.stdout, stderr=r.stderr,
                         elapsed_seconds=time.time()-started))
    (b / 'R182I-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    print(json.dumps(dict(step=step, returncode=r.returncode,
                         elapsed_seconds=round(time.time()-started, 2))), flush=True)
    assert r.returncode in allowed, 'Unexpected command failure; logs preserved'

run('build_independent_unrouted_space_model', [py, str(dev/'scripts/build_trial.py'),
    str(source), str(dest), str(b/'R182I-plan.json')])
c = Copper(dest / board_name)
before_outline_sha = c.sha
expected = {
    '2970bcb0-ffff-463d-9a8d-088788b9c374': ((0,35),(0,0),(0,40),(0,0)),
    '7ba022ad-f86c-4f89-a1df-f73c3bd442d8': ((70,0),(70,35),(70,0),(70,40)),
    '81451644-bff0-4371-b66d-2f2b40af3e26': ((70,35),(0,35),(70,40),(0,40)),
}
changed = []
for d in c.board.GetDrawings():
    if uid(d) not in expected:
        continue
    a, z, na, nz = expected[uid(d)]
    assert c.board.GetLayerName(d.GetLayer()) == 'Edge.Cuts'
    assert xy(d.GetStart()) == a and xy(d.GetEnd()) == z
    d.SetStart(pcb.VECTOR2I(int(na[0]*1e6),int(na[1]*1e6)))
    d.SetEnd(pcb.VECTOR2I(int(nz[0]*1e6),int(nz[1]*1e6)))
    changed.append(dict(uuid=uid(d), before=[a,z], after=[na,nz]))
assert len(changed) == 3
pcb.SaveBoard(str(dest/board_name), c.board)
write('R182I-outline-edit.json', dict(
    source_sha256=expected_sha, before_outline_edit_sha256=before_outline_sha,
    after_outline_edit_sha256=sha(dest/board_name), changes=changed,
    outline_mm=[70,40], old_outline_mm=[70,35], area_increase_mm2=350,
    area_increase_fraction=350/2450, thickness_mm=1.6,
    direction='Native PCB +Y; robot installation direction not established',
    ground_power_zones_extended=False, fixed_mounts_retained=True,
    lower_mount_to_edge_mm={'source':2.5,'proposal':7.5},
    adopted=False, routing_complete=False, physical_fit='NOT_TESTED',
    unsupported_extension_strength='NOT_TESTED', manufacturing_release=False))
run('native_refill_and_DRC_of_unrouted_space_model', [
    '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli', 'pcb', 'drc',
    '--format','json','--schematic-parity','--refill-zones','--save-board',
    '--severity-all','--exit-code-violations','-o',str(b/'R182I-drc.json'),
    str(dest/board_name)], (0,5))

s = Copper(source/board_name)
t = Copper(dest/board_name)
sf = {f.GetReference():f for f in s.footprints}
tf = {f.GetReference():f for f in t.footprints}
assert set(sf) == set(tf)
changed_refs = []
for ref,f in sf.items():
    g = tf[ref]
    same = (xy(f.GetPosition()), f.GetOrientationDegrees(), int(f.GetLayer())) == (
        xy(g.GetPosition()), g.GetOrientationDegrees(), int(g.GetLayer()))
    if not same:
        changed_refs.append(ref)
        continue
    sp = {p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in f.Pads()}
    tp = {p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in g.Pads()}
    assert sp == tp, ref
assert sorted(changed_refs) == ['C301','U301']
assert {uid(v):via_snapshot(s.board,v) for v in s.vias} == {
    uid(v):via_snapshot(t.board,v) for v in t.vias}
sz = {uid(z):z for z in s.board.Zones() if not z.GetIsRuleArea()}
tz = {uid(z):z for z in t.board.Zones() if not z.GetIsRuleArea()}
assert set(sz) == set(tz)
assert all(polyset(z.Outline()).equals(polyset(tz[k].Outline())) for k,z in sz.items())
edges = [d for d in t.board.GetDrawings() if t.board.GetLayerName(d.GetLayer())=='Edge.Cuts']
assert len(edges) == 4
coords = [xy(v) for d in edges for v in (d.GetStart(), d.GetEnd())]
assert (min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)) == (0,0,70,40)
assert abs(t.board.GetDesignSettings().GetBoardThickness()/1e6-1.6) < 1e-9
assert t.board.GetCopperLayerCount() == 6
unchanged_members = [name for name,h in source_members.items()
                     if name != board_name and (dest/name).is_file() and sha(dest/name)==h]
assert len(unchanged_members) == len(source_members)-1
assert source_members == {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
drc = json.loads((b/'R182I-drc.json').read_text())
write('R182I-space-check.json', dict(
    scope=__doc__, source_sha256=expected_sha, proposal_sha256=t.sha,
    fixed_footprints_checked=len(sf)-2, moved_footprints=changed_refs,
    fixed_connectors=[r for r in sorted(sf) if r.startswith('J')],
    fixed_mounts=[r for r in sorted(sf) if r.startswith('H')],
    fixed_core_pin_count=sum(len(list(sf[r].Pads())) for r in ('J101','J102')),
    vias_unchanged=len(s.vias), original_ground_vias_unchanged=sum(v.GetNetname()=='GND' for v in s.vias),
    native_power_and_ground_zone_outlines_unchanged=len(sz),
    unchanged_non_PCB_members=unchanged_members,
    unconnected_items=len(drc['unconnected_items']), other_DRC=len(drc['violations']),
    schematic_parity=len(drc['schematic_parity']),
    placement_scope_check='PASS', electrical_acceptance='FAIL_UNROUTED',
    physical_fit='NOT_TESTED', adopted=False, manufacturing_release=False))
print(json.dumps(dict(proposal=str(dest/board_name),sha256=t.sha,
    unconnected_items=len(drc['unconnected_items']),other_DRC=len(drc['violations']),
    fixed_footprints=len(sf)-2,unchanged_members=len(unchanged_members),adopted=False)),flush=True)
