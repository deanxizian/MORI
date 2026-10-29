"""Exercise invalid movement plans and verify the actual native round trip.

These are builder integrity tests, not electrical or manufacturing validation.
"""
import contextlib,copy,hashlib,io,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import build
b=Path('robot/.state/c3-completion/trials');out=b/'R145-via-move-guards';out.mkdir(exist_ok=False)
src=Path('robot/hardware/driver/development/native');mini=out/'minimal-source';mini.mkdir()
for suffix in ['.kicad_pcb','.kicad_pro','.kicad_dru']:
 shutil.copy2(src/('MORI_Interface_C3'+suffix),mini/('MORI_Interface_C3'+suffix))
c=Copper(mini/'MORI_Interface_C3.kicad_pcb');vid='48a80751-1835-4880-839b-49e61af8d8d1';v=c.by_id[vid]
spec={'uuid':vid,'source_expected':via_snapshot(c.board,v),'position_mm':[33.575,18.7],'reason':'Guard test only'}
base={'revision':'R145-via-guard','board_sha256':c.sha,'move_vias':[spec]}
cases=[]
def add(name,mutate,expected):
 p=copy.deepcopy(base);mutate(p);cases.append((name,p,expected))
add('wrong-source-hash',lambda p:p.update(board_sha256='0'*64),'Plan source PCB hash does not match')
add('missing-source-hash',lambda p:p.pop('board_sha256'),'Via movement requires an exact source board hash')
add('wrong-source-drill',lambda p:p['move_vias'][0]['source_expected'].update(drill_mm=.25),'Moved non-ground via snapshot mismatch')
add('missing-reason',lambda p:p['move_vias'][0].pop('reason'),'Via move requires a distinct finite position')
add('nonfinite-position',lambda p:p['move_vias'][0].update(position_mm=[float('nan'),18.7]),'Via move requires a distinct finite position')
add('unchanged-position',lambda p:p['move_vias'][0].update(position_mm=[33.325,18.7]),'Via move requires a distinct finite position')
add('duplicate-move',lambda p:p['move_vias'].append(copy.deepcopy(p['move_vias'][0])),'Duplicate or conflicting via move')
ground=next(v for v in c.vias if v.GetNetname()=='GND')
add('ground-move',lambda p:p['move_vias'][0].update(uuid=uid(ground),source_expected=via_snapshot(c.board,ground)),'Moved non-ground via snapshot mismatch')
results=[]
for name,plan,expected in cases:
 path=out/(name+'.json');path.write_text(json.dumps(plan,indent=2)+'\n')
 log=io.StringIO()
 try:
  with contextlib.redirect_stdout(log):build(mini,out/name,path)
 except ValueError as e:
  result={'case':name,'status':'PASS' if str(e).startswith(expected) else 'FAIL','exception':str(e)}
 else:result={'case':name,'status':'FAIL','exception':None}
 results.append(result)
candidate=Copper(b/'R145E/MORI_Interface_C3.kicad_pcb')
expected={**spec['source_expected'],'position_mm':spec['position_mm']}
results.append({'case':'actual-native-refilled-roundtrip','status':'PASS' if via_snapshot(candidate.board,candidate.by_id[vid])==expected else 'FAIL','candidate_sha256':candidate.sha,'snapshot':via_snapshot(candidate.board,candidate.by_id[vid])})
source_unchanged=hashlib.sha256((src/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()==c.sha
report={'scope':__doc__,'source_sha256':c.sha,'source_unchanged':source_unchanged,'results':results,'status':'PASS' if source_unchanged and all(r['status']=='PASS' for r in results) else 'FAIL'}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['status']=='PASS'
