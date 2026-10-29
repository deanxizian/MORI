"""Build a disposable trial with one exact, declared In2 power-zone expansion.

This does not relax a rule, keepout, priority, clearance, thermal setting or minimum
thickness. Production planned-delta support is required before any adoption.
"""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import build,set_outline
from shapely.geometry import Polygon
source,destination,plan_path=map(Path,sys.argv[1:4]);plan=json.loads(plan_path.read_text());build(source,destination,plan_path)
p=destination/'MORI_Interface_C3.kicad_pcb';board=pcb.LoadBoard(str(p));zones={uid(z):z for z in board.Zones()};old_shapes={u:polyset(z.Outline()) for u,z in zones.items()}
records=[];modified=set()
for spec in plan['power_zone_expansions']:
 u=spec['uuid'];assert u not in modified;modified.add(u);z=zones[u]
 expected=spec['source_expected'];actual={'net':z.GetNetname(),'layers':[l for l in LAYERS if z.IsOnLayer(board.GetLayerID(l))],'priority':z.GetAssignedPriority(),'outline_wkt':old_shapes[u].wkt}
 assert actual==expected,(actual,expected)
 assert not z.GetIsRuleArea() and actual['layers']==['In2.Cu'] and actual['net']=='/09 {slash} Head_Buck/HEAD_BUCK_IN'
 patch=Polygon(spec['union_patch_mm']);assert patch.is_valid and not patch.is_empty
 target=old_shapes[u].union(patch);assert target.geom_type=='Polygon' and target.is_valid and target.intersection(Polygon([(0,0),(70,0),(70,35),(0,35)])).equals(target)
 assert target.covers(old_shapes[u]) and target.area-old_shapes[u].area<2
 set_outline(z,target);records.append({'uuid':u,'source_expected':actual,'patch_mm':spec['union_patch_mm'],'target_outline_wkt':target.wkt,'added_area_mm2':target.area-old_shapes[u].area})
pcb.SaveBoard(str(p),board);r=pcb.LoadBoard(str(p));saved={uid(z):z for z in r.Zones()};assert set(saved)==set(zones)
for u in zones:
 target=next((Polygon(spec['union_patch_mm']).union(old_shapes[u]) for spec in plan['power_zone_expansions'] if spec['uuid']==u),old_shapes[u])
 assert polyset(saved[u].Outline()).symmetric_difference(target).area<1e-9,u
receipt={'scope':__doc__,'revision':plan['revision'],'source_board_sha256':hashlib.sha256((source/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest(),'board_sha256_before_refill':hashlib.sha256(p.read_bytes()).hexdigest(),'expansions':records,'native_keepout_shapes_retained':all(old_shapes[u].equals(polyset(saved[u].Outline())) for u,z in zones.items() if z.GetIsRuleArea()),'adoption':'NOT_ADOPTED'}
(plan_path.parent/(plan['revision']+'-zone-edit.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'zone_expansions':len(records),'added_area_mm2':sum(x['added_area_mm2'] for x in records)}),flush=True)
