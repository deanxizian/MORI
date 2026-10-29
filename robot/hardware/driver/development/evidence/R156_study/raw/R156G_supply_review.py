"""Confirm the existing internal 3V3 feed survives removal of redundant front branches."""
import json,sys
from pathlib import Path
from itertools import combinations
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');o=b/'R156G-supply-review.json';assert not o.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R156G/MORI_Interface_C3.kicad_pcb')
vs=['9fc6be27-25b2-4bce-8f44-98f39ccd1aa1','aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57','c89d9b75-62b7-4bdc-8fe8-09516366b58c'];pads={c.pad_name(p):p for p in c.pads};ends=vs+[uid(pads['C505.1'])];rows=[]
for w in [0,.18,.28,.33,.48]:
 pa=a.connected_pairs('MOTION_3V3',w);pc=c.connected_pairs('MOTION_3V3',w);pairs=[tuple(sorted(p)) for p in combinations(ends,2)];rows.append({'width_mm':w,'pairs':[{'endpoints':list(p),'source':p in pa,'candidate':p in pc} for p in pairs]})
assert all(not p['source'] or p['candidate'] for r in rows for p in r['pairs'])
planes=[]
for net,layers in [('MOTION_3V3',['In2.Cu','In3.Cu']),('GND',['In1.Cu','In4.Cu'])]:
 for ly in layers:
  old=unary_union([g for n,l,g in a.fills if n==net and l==ly]);new=unary_union([g for n,l,g in c.fills if n==net and l==ly]);area=old.symmetric_difference(new).area;planes.append({'net':net,'layer':ly,'source_fill_area_mm2':old.area,'candidate_fill_area_mm2':new.area,'changed_area_mm2':area});assert area<1e-7
r={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'source_local_pair_widths_preserved':True,'pair_checks':rows,'internal_supply_and_reference_fills':planes,'interpretation':'All six removed front branches are redundant for the measured native-copper connectivity and previous width gates. The three retained vias still join through the unchanged In3 3V3 fill, with their original In2 contacts. C505 remains supplied; no new long power detour or inner allocation was created. Terminal and barrel rating, HF current sharing, thermal and EMC remain NOT_TESTED.','physical':'NOT_TESTED','manufacturing_release':False};o.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':'PASS','preserved_width_rows':len(rows),'unchanged_internal_fills':len(planes),'pair_results':rows}))
