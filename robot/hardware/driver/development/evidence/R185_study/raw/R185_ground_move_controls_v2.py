"""Native-source positive and rejection controls for explicit GND movement."""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import Copper
from ground_via_moves import validate_ground_via_moves
b=Path('robot/.state/c3-completion/trials');out=b/'R185-ground-move-controls-v2.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/'R185I-plan.json').read_text());rows=[]
positive=validate_ground_via_moves(c.board,plan);assert len(positive)==1
rows.append(dict(name='source_bound_shorter_return',expected='ALLOW',actual='ALLOW',status='PASS'))
def reject(name,mutate):
    p=copy.deepcopy(plan);mutate(p)
    try:validate_ground_via_moves(c.board,p)
    except (ValueError,KeyError,TypeError) as e:
        rows.append(dict(name=name,expected='REJECT',actual='REJECT',error=str(e),status='PASS'))
    else:raise AssertionError('Unsafe plan accepted: '+name)
reject('missing_source_hash',lambda p:p.pop('board_sha256'))
reject('source_drill_changed',lambda p:p['move_ground_vias'][0]['source_expected'].update(drill_mm=.4))
reject('source_net_changed',lambda p:p['move_ground_vias'][0]['source_expected'].update(net='MOTION_3V3'))
reject('nonfinite_destination',lambda p:p['move_ground_vias'][0].update(position_mm=[float('nan'),8.4]))
reject('duplicate_ground_move',lambda p:p['move_ground_vias'].append(copy.deepcopy(p['move_ground_vias'][0])))
reject('conflicting_non_ground_move',lambda p:p.update(move_vias=[copy.deepcopy(p['move_ground_vias'][0])]))
reject('omitted_source_contact',lambda p:p['move_ground_vias'][0].update(source_contact_track_uuids=[]))
reject('abandoned_direct_return',lambda p:p['move_ground_vias'][0].update(return_paths=[]))
reject('missing_source_return_segment',lambda p:p['move_ground_vias'][0]['return_paths'][0].update(source_track_uuids=['1e6e4d91-7a6d-45e9-b841-a86fe7e91a87']))
reject('missing_replacement_return',lambda p:p['move_ground_vias'][0]['return_paths'][0].update(replacement_route_indices=[]))
reject('return_wrong_net',lambda p:p['routes'][0].update(net='MOTION_3V3'))
reject('return_nan_width',lambda p:p['routes'][0].update(width_mm=float('nan')))
reject('return_infinite_width',lambda p:p['routes'][0].update(width_mm=float('inf')))
reject('return_non_numeric_width',lambda p:p['routes'][0].update(width_mm='0.2'))
reject('return_narrowed',lambda p:p['routes'][0].update(width_mm=.15))
reject('return_wrong_face',lambda p:p['routes'][0].update(layer='F.Cu'))
reject('return_lengthened',lambda p:p['routes'][0].update(points_mm=[[57.9,9.325],[57,9.325],[57,8.4],[57.9,8.4]]))
reject('return_not_to_via',lambda p:p['routes'][0].update(points_mm=[[57.9,9.325],[57.9,8.5]]))
reject('anchor_pad_moved',lambda p:p.update(translations=[dict(reference='C601')]))
v=c.by_id[plan['move_ground_vias'][0]['uuid']];v.SetLocked(True)
reject('locked_via',lambda p:None);v.SetLocked(False)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,positive=positive,checks=rows,status='PASS',source_saved=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',checks=len(rows))))
