"""Native save/reload tests for opt-in rotation with fixed global via cutouts."""
import json,sys
from pathlib import Path
from shapely.affinity import rotate,translate
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import build
b=Path('robot/.state/c3-completion/trials');out=b/'R147-guard-checks';out.mkdir(exist_ok=False)
source=Path('robot/hardware/driver/development/native');a=Copper(source/'MORI_Interface_C3.kicad_pcb')
old=[k for k in a.keepouts if k['name'].startswith('BODY_R1601_')]
body=unary_union([k['shape'] for k in old if k['tracks']]);via=unary_union([k['shape'] for k in old if k['vias']]);holes=body.difference(via)
assert holes.area>0
rows=[]
for name,angle,delta,opt,reconstruct in [('rotate180',90,[2.4,.9],True,True),('rotate90',0,[2.4,.9],True,True),('rotate270',180,[2.4,.9],True,True),('same_position180',90,[0,0],True,True),('old_translation',-90,[.05,.425],False,True),('reject_implicit',90,[2.4,.9],False,True),('reject_no_reconstruction',90,[2.4,.9],True,False)]:
 spec={'reference':'R1601','from_mm':[38.6,16.9],'delta_mm':delta,'rotation_deg':angle,'reconstruct_fixed_via_guards':reconstruct,'rotate_fixed_via_guards':opt}
 p={'revision':'R147_guard_'+name,'board_sha256':a.sha,'translations':[spec]};file=out/(name+'.json');file.write_text(json.dumps(p,indent=2)+'\n')
 try:build(source,out/name,file)
 except ValueError as e:
  assert name.startswith('reject_'),str(e);rows.append({'case':name,'status':'PASS','rejected':str(e)});continue
 assert not name.startswith('reject_')
 z=Copper(out/name/'MORI_Interface_C3.kicad_pcb');new={k['id']:k for k in z.keepouts}
 target=translate(rotate(body,-(angle+90),origin=(38.6,16.9)),xoff=delta[0],yoff=delta[1]).difference(holes)
 actual=unary_union([new[k['id']]['shape'] for k in old if k['vias']]);error=target.symmetric_difference(actual).area
 assert error<1e-7,(name,error)
 for k in old:
  assert all(new[k['id']][key]==k[key] for key in ['name','layers','tracks','vias','pads','copper'])
  if k['tracks']:
   expected=translate(rotate(k['shape'],-(angle+90),origin=(38.6,16.9)),xoff=delta[0],yoff=delta[1]);assert expected.symmetric_difference(new[k['id']]['shape']).area<1e-7
 assert set(uid(v) for v in a.vias)==set(uid(v) for v in z.vias)
 for v in a.vias:assert via_snapshot(a.board,v)==via_snapshot(z.board,z.by_id[uid(v)])
 rows.append({'case':name,'status':'PASS','native_readback_area_error_mm2':error,'all_original_via_snapshots_unchanged':True})
assert hashlib.sha256((source/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()==a.sha
(out/'result.json').write_text(json.dumps({'scope':__doc__,'source_sha256':a.sha,'checks':rows,'status':'PASS'},indent=2)+'\n');print(json.dumps(rows),flush=True)
