"""Read actual R148E ADC/sense group positions before proposing any layout change."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b = Path('robot/.state/c3-completion/trials')
out = b / 'R149-source.json'
assert not out.exists()
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
refs = ['U1001','U1101','R1101','R1102','C1101','C1102','R1001','R1002','R1003','R1021','R1022','R1031','R1032','R1033']
rows = []
for f in c.footprints:
    if f.GetReference() not in refs: continue
    rows.append(dict(ref=f.GetReference(), value=f.GetValue(), layer=c.board.GetLayerName(f.GetLayer()), position=xy(f.GetPosition()), angle=f.GetOrientationDegrees(), pads=[dict(name=c.pad_name(p),net=p.GetNetname(),position=xy(p.GetPosition()),size=xy(p.GetSize()),uuid=uid(p)) for p in f.Pads()]))
nets = ['/ACT_CURRENT_FILTERED','Net-(U1101-OUT)','Net-(U1001-D1_{slash}_BAT_ADC)','Net-(U1001-D2_{slash}_WHEEL_ADC)','/01 {slash} Core/BAT_ADC']
detail = {}
for net in nets:
    detail[net] = dict(groups=[dict(pads=g['pads'],layers={ly:list(s.bounds) for ly,s in g['layers'].items()}) for g in groups(c,net)], tracks=[dict(uuid=uid(t),layer=c.board.GetLayerName(t.GetLayer()),width=t.GetWidth()/1e6,start=xy(t.GetStart()),end=xy(t.GetEnd())) for t in c.segments if t.GetNetname()==net],vias=[dict(uuid=uid(v),position=xy(v.GetPosition())) for v in c.vias if v.GetNetname()==net])
reg=json.loads(Path('robot/hardware/driver/development/evidence/R148E/regression.json').read_text())
data=dict(scope=__doc__,source_sha256=c.sha,footprints=rows,nets=detail,adjacency=[r for r in reg['critical_placement'] if any(r[k].split('.')[0] in refs for k in ['a','b'])])
out.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
