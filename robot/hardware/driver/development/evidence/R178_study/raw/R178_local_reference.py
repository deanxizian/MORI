"""Measure a declared R178 candidate's opposite DVDT overlap and ground.

This is geometric source evidence for a local prototype routing review, not a
field simulation, thermal result or qualification of the complete eFuse layout.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
revision=sys.argv[1] if len(sys.argv)>1 else 'R178G'
c=Copper(str(b/revision/'MORI_Interface_C3.kicad_pcb'))
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
new=unary_union([c.shapes[uid(t),'F.Cu'] for t in c.segments if uid(t) not in a.by_id and t.GetNetname()=='/FAULT_N'])
overlap=new.intersection(c.copper['Net-(U1201-DVDT)','B.Cu'])
planes={ly:c.copper['GND',ly] for ly in ['In1.Cu','In4.Cu']}
rows=dict(scope=__doc__,source_sha256=a.sha,board_sha256=c.sha,
          new_FAULT_stroke_mm2=new.area,opposite_DVDT_copper_overlap_mm2=overlap.area,
          overlap_unshielded_mm2={ly:overlap.difference(g).area for ly,g in planes.items()},
          overlap_unshielded_by_both_mm2=overlap.difference(unary_union(list(planes.values()))).area,
          inductor_projections={ref:new.intersection(fab(next(f for f in c.footprints if f.GetReference()==ref))).area for ref in ['L701','L901']},
          physical_noise_or_thermal_qualification='NOT_TESTED')
p=b/(revision+'-local-reference-review.json');assert not p.exists();p.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
