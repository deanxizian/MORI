"""Correct a report count: J101/J102 are 60 pads; include eight J105 core pads."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import Copper,xy
b=Path('robot/.state/c3-completion/trials')
p=b/'R182I-space-check.json';report=json.loads(p.read_text())
assert report['fixed_core_pin_count']==60
backup=b/'R182I-space-check-initial-core-count.json'
with backup.open('xb') as f:f.write(p.read_bytes())
s=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
t=Copper(b/'R182I/MORI_Interface_C3.kicad_pcb')
assert s.sha==report['source_sha256'] and t.sha==report['proposal_sha256']
rows=[]
for ref in ['J101','J102','J105']:
    a=next(f for f in s.footprints if f.GetReference()==ref)
    z=next(f for f in t.footprints if f.GetReference()==ref)
    source={p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in a.Pads()}
    target={p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in z.Pads()}
    assert source==target
    rows.append(dict(reference=ref,pad_count=len(source),pads_fixed=True))
assert sum(r['pad_count'] for r in rows)==68
report['fixed_core_pin_count']=68
report['fixed_core_pin_check']=rows
report['count_correction']='Initial count 60 included J101/J102 only; all eight J105 pads are also individually checked unchanged. No PCB edit.'
p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(rows))
