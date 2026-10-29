"""Validate actual offset pad exits without allowing arbitrary source endpoints."""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import Copper
from ground_via_moves import validate_ground_via_moves
b=Path('robot/.state/c3-completion/trials');out=b/'R186-ground-exit-controls.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/'R186A-plan.json').read_text());rows=[]
for name,p in [('native_offset_exit',plan),('existing_centre_exit',json.loads((b/'R185I-plan.json').read_text()))]:
 r=validate_ground_via_moves(c.board,p);assert len(r)==1
 rows.append(dict(name=name,status='PASS',result=r))
def reject(name,change):
 p=copy.deepcopy(plan);change(p['move_ground_vias'][0]['return_paths'][0])
 try:validate_ground_via_moves(c.board,p)
 except ValueError as e:rows.append(dict(name=name,status='PASS',rejected=str(e)))
 else:raise AssertionError('Invalid source exit accepted: '+name)
reject('outside_pad',lambda p:p.update(source_pad_exit_mm=[52.4,15.275]))
reject('inside_pad_but_not_actual_track_endpoint',lambda p:p.update(source_pad_exit_mm=[52.2,15.275]))
reject('nonfinite_exit',lambda p:p.update(source_pad_exit_mm=[float('nan'),15.275]))
reject('missing_offset_declaration',lambda p:p.pop('source_pad_exit_mm'))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,status='PASS',checks=rows,source_saved=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',checks=len(rows))))
