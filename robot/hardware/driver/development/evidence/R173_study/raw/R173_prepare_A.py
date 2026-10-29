"""Explicit native eight-part supervisor/INA300 placement trial, unadopted.

The supervisor moves above/left while INA300 moves down. All 114 source GND
vias, fixed interfaces, original electrical definitions and rule thresholds stay.
Two source supply transfers move explicitly; obsolete CT transfer exits after
all CT leads are replaced. The preparation is deliberately incomplete and must
not replace the accepted board. Native checks decide which routes need revision.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R173A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');fps={f.GetReference():f for f in c.footprints}
screen=json.loads((b/'R173-local-group-screen.json').read_text());assert c.sha==screen['source_sha256']
group=screen['best_groups'][0]
poses={p['reference']:(p['position_mm'],p['rotation_deg']) for p in group['parts']}
poses.update(U1701=([46.75,14],0),R1701=([49.9,17],0),C1701=([51.4,11],90),R1706=([42.75,16],90),R1707=([47,8.875],270))
plan=dict(revision='R173A',scope=__doc__,board_sha256=c.sha,translations=[],delete_copper=sorted(set(screen['prospectively_retired_tracks'])|set(group['additional_track_dependencies'])),deleted_copper_expected={},move_vias=[],remove_obsolete_vias=[],vias=[],routes=[])
for ref,(pos,a) in poses.items():
 f=fps[ref];old=list(xy(f.GetPosition()));spec=dict(reference=ref,from_mm=old,delta_mm=[round(pos[i]-old[i],6) for i in range(2)],rotation_deg=a)
 if ref in ['U1302','U1701']:
  spec.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True,repartition_fixed_via_guards=True)
 if ref in ['R1310','R1707']:
  spec['side_change']=dict(from_face=c.board.GetLayerName(f.GetLayer()),to_face='B.Cu' if ref=='R1310' else 'F.Cu',from_rotation_deg=f.GetOrientationDegrees(),axis='LEFT_RIGHT',reason='Grouped supervisor and INA300 relocation; keep original two-pad resistor identity, value, pin numbers and networks.')
 if pos!=old or a!=f.GetOrientationDegrees() or 'side_change' in spec:plan['translations'].append(spec)
for u in plan['delete_copper']:
 t=c.by_id[u];plan['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
for u,pos in [('4150016a-d870-4d6e-beae-177f9b3cdd3a',[45.5,10.7]),('c9ef7bb5-bef9-48b7-b4cf-23501fe0a859',[44.5,7]),('c89d9b75-62b7-4bdc-8fe8-09516366b58c',[50.5,13])]:
 v=c.by_id[u];plan['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,v),position_mm=pos,reason='Restore source supply outside the relocated IC pads and original body guards. Original distribution and widths must pass after refill.'))
v=c.by_id[screen['prospectively_obsolete_CT_via']]
plan['remove_obsolete_vias']=[dict(uuid=uid(v),source_expected=via_snapshot(c.board,v),remaining_contact_layers=[],reason='All source CT leads are explicitly retired; R1310 and U1302 now share B.Cu and will receive a direct CT connection. No other source CT pads or vias exist.')]
def route(net,ly,width,points):plan['routes'].append(dict(net=net,layer=ly,width_mm=width,points_mm=points))
# Restore two displaced source supply transfers; full refill/reference still required.
route('UPS_BAT_IN','F.Cu',.3,[[45.29,11.465],[45.5,11.255],[45.5,10.7]])
route('MOTION_5V','B.Cu',.3,[[44.5,6.4],[44.5,7]])
# Reuse source 3V3 upper transfer and retain its original F branch.
old=c.by_id['bc3e9793-b9cd-54b1-b44c-64b91f6e9a06'];route(old.GetNetname(),'F.Cu',old.GetWidth()/1e6,[list(xy(old.GetStart())),list(xy(old.GetEnd()))])
# Short VDD/SENSE tie on the relocated supervisor. Both pins already share 3V3.
route('MOTION_3V3','B.Cu',.2,[[44.3875,9.25],[44.8,9.25],[44.8,10.2],[44.3875,10.2]])
assert all(r['net'] in {n.GetNetname() for n in c.board.GetNetInfo().NetsByNetcode().values()} for r in plan['routes'])
out.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(plan=str(out),translations=len(plan['translations']),retired_tracks=len(plan['delete_copper']),moved_vias=len(plan['move_vias']),routes=len(plan['routes']))))
