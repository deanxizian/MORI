"""Readback and negative controls for the independent mixed-rule trial only."""
import json,sys,hashlib
from pathlib import Path
from shapely import from_wkb
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_settings
b=Path('robot/.state/c3-completion/trials');out=b/'R184D-mixed-guard-readback.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(str(b/'R184D/MORI_Interface_C3.kicad_pcb'))
record=json.loads((b/'R184D-mixed-guard-build.json').read_text())[0]
az={uid(z):z for z in a.zones};cz={uid(z):z for z in c.zones}
def test_one(u):
    r=record['guards'][u];z=cz[u]
    return zone_settings(c.board,z)==r['settings']==zone_settings(a.board,az[u]) and polyset(z.Outline()).symmetric_difference(from_wkb(bytes.fromhex(r['expected_wkb_hex']))).area<1e-7
checks={u:test_one(u) for u in record['guards']};assert len(checks)==9 and all(checks.values())
controls=[]
u=next(u for u in record['guards'] if cz[u].GetDoNotAllowVias() and not cz[u].GetDoNotAllowTracks())
z=cz[u];z.SetDoNotAllowVias(False);controls.append(dict(change='remove via prohibition in memory',rejected=not test_one(u)));z.SetDoNotAllowVias(True)
z.Move(pcb.VECTOR2I(10000,0));controls.append(dict(change='translate one via guard by 0.01 mm in memory',rejected=not test_one(u)));z.Move(pcb.VECTOR2I(-10000,0))
assert all(r['rejected'] for r in controls) and all(test_one(u) for u in record['guards'])
ground=[v for v in a.vias if v.GetNetname()=='GND'];assert len(ground)==114
assert all(uid(v) in c.by_id and via_snapshot(a.board,v)==via_snapshot(c.board,c.by_id[uid(v)]) for v in ground)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
out.write_text(json.dumps(dict(status='PASS',scope=__doc__,source_sha256=a.sha,board_sha256=c.sha,
    guard_checks=checks,negative_controls=controls,original_ground_vias_retained=114,
    production_builder_modified=False,full_planned_delta='NOT_RUN; candidate loses original connections',manufacturing_release=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',guards=len(checks),negative_controls=len(controls),GND_vias=len(ground))))
