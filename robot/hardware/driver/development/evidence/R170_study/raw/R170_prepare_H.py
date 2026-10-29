"""Half-turn joint native comparison, with explicit passive/copper transforms.

Instantiate the return-distance-scored candidate and its short local bypass
leads. All 325 original vias stay fixed in this first native test. Prospective
via movement from the placement screen is NOT applied or claimed verified.
Every original link, direct RLIMIT return and power/reference path remains a
mandatory acceptance condition. This is an unadopted comparison.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170H-plan.json';assert not out.exists();p=json.loads((b/'R169D-plan.json').read_text());s=json.loads((b/'R170-cell-return-score.json').read_text());q=s['joint_candidates'][0];c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');fps={f.GetReference():f for f in c.footprints};assert c.sha==p['board_sha256']
for row in q['parts']:
 ref=row['reference'];f=fps[ref];old=list(xy(f.GetPosition()));spec=dict(reference=ref,from_mm=old,delta_mm=[round(x-y,6) for x,y in zip(row['position_mm'],old)],rotation_deg=row['rotation_deg'])
 if row['face']!=c.board.GetLayerName(f.GetLayer()):spec['side_change']=dict(from_face=c.board.GetLayerName(f.GetLayer()),to_face=row['face'],from_rotation_deg=f.GetOrientationDegrees(),axis='LEFT_RIGHT',reason='Joint INA300 input and RLIMIT return comparison; source pad numbers, values and networks are preserved.')
 p['translations'].append(spec)
for id_ in s['prospectively_retired_tracks']:
 if id_ in p['delete_copper']:continue
 t=c.by_id[id_];assert isinstance(t,pcb.PCB_TRACK) and not isinstance(t,pcb.PCB_VIA);p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'] += [dict(net='MOTION_3V3',layer='B.Cu',width_mm=.2,points_mm=[[43.25,11.35],[43.8,11.35],[44.0,11.55],[44.0,11.85],[45.05,11.85]]),dict(net='GND',layer='B.Cu',width_mm=.2,points_mm=[[43.25,12.9],[43.8,12.9],[44.0,12.7],[44.0,12.35],[45.05,12.35]])]
p.update(revision='R170H',scope=__doc__,placement_comparison='R170-cell-return-score.json',selected_candidate_index=0,adoption_prohibited=True);out.write_text(json.dumps(p,indent=2)+'\n');print(out)
