"""Read-only source-to-current fixed interface and component identity review."""
import json
import sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper, xy

a = Copper('robot/.state/c3-completion/baseline/MORI_Interface_C3.kicad_pcb')
b = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
old = {f.GetReference(): f for f in a.footprints}
new = {f.GetReference(): f for f in b.footprints}
assert set(old) == set(new) and len(new) == 215
checks = {}
for ref, f in old.items():
    g = new[ref]
    checks[ref + '_value_and_package'] = f.GetValue() == g.GetValue() and f.GetFPID().GetLibItemName() == g.GetFPID().GetLibItemName()
    ap = {str(p.GetNumber()): p for p in f.Pads()}
    bp = {str(p.GetNumber()): p for p in g.Pads()}
    checks[ref + '_pin_nets'] = set(ap) == set(bp) and all(ap[n].GetNetname() == bp[n].GetNetname() for n in ap)
    if ref.startswith(('J', 'H')):
        checks[ref + '_fixed_interface'] = (xy(f.GetPosition()) == xy(g.GetPosition()) and f.GetOrientationDegrees() == g.GetOrientationDegrees()
            and f.GetLayer() == g.GetLayer() and all(xy(ap[n].GetPosition()) == xy(bp[n].GetPosition()) and xy(ap[n].GetSize()) == xy(bp[n].GetSize()) and xy(ap[n].GetDrillSize()) == xy(bp[n].GetDrillSize()) for n in ap))
def edges(c):
    return sorted((str(d.GetShape()), xy(d.GetStart()), xy(d.GetEnd())) for d in c.board.GetDrawings() if c.board.GetLayerName(d.GetLayer()) == 'Edge.Cuts')
checks['outline'] = edges(a) == edges(b)
checks['six_layers_and_thickness'] = a.board.GetCopperLayerCount() == b.board.GetCopperLayerCount() == 6 and a.board.GetDesignSettings().GetBoardThickness() == b.board.GetDesignSettings().GetBoardThickness()
result = dict(status='PASS' if all(checks.values()) else 'FAIL', source_sha256=a.sha, current_sha256=b.sha,
              checks=checks, fixed_connectors=[x for x in old if x.startswith('J')],
              fixed_mounting_holes=[x for x in old if x.startswith('H')],
              scope=__doc__, mechanical_fit='NOT_TESTED', manufacturing_release=False)
Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'checks'}))
raise SystemExit(not all(checks.values()))
