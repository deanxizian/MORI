"""Independent five-resistor permutation for RAW access, restoring all local nets.

This is an unaccepted diagnostic native candidate. It reuses two non-GND holes,
retains the fixed outline/interfaces and does not claim the full RAW feed is routed.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R190A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
wheel='Net-(U402-1Y)';bus='/03 {slash} Motor_Buses/WHEEL_BUS';ov='Net-(U1301-INB-_{slash}_OV)';middle='Net-(R1304-~-Pad1)';lower='Net-(R1305-~-Pad1)'
deleted=['38b1aa1f-6d6c-5391-ae66-8dc9df61b001','ad23fc9d-55cc-5e3c-910c-9b49312999af',
'06516b20-ba36-405f-86bc-58bf187b0ee4','364a8831-1edb-4a26-9963-10aa62748be3',
'42236b96-3e31-4ab6-8c05-84597540bf84','62f4fe96-15c4-4c6e-8659-1450215f3dcf','73be6ccd-56a9-4921-afe5-56eaba79e09b',
'65d3606e-9501-4392-b131-807e4a98ceca','cee78bab-4bcc-4f61-88b9-44e78cdcd967',
'26ed05e0-da76-4d4f-bf63-48373d2464df','767f0376-a035-4a3f-a407-9177b9773118','ae265992-0a5f-4917-908d-d4813e01b63a',
'400071c8-db07-41c0-9e4e-8d2d15d5e57b','586926b4-93f6-4f54-929b-7781ab7ee7d9','b2909eee-2eec-445e-acf1-476a88d3a25a',
'17ba0129-9826-4ed3-81b0-f1ae47427144','b2c91013-fbf9-4e6e-81d5-36b2363b7987','ca502b74-cb95-4ee5-a0c1-707a1bbb85a9','f8b0c5de-3049-48b4-9985-faffdd80f24e',
'239cbb8f-1d22-5318-be72-fedba62fd843','374d2143-8352-5a63-ab90-827dc20f4859','6b356544-a1c6-5e8e-b788-f377e9bd7839','7a51b4b8-8a06-528b-9f1b-ddbcc0a2fafe','93e69403-30ea-5ee0-9acc-3de8618ec612','ae500990-78cd-5224-bbcf-9287210d8be3','f665914c-f4cf-5689-a5d0-eb0eabc328cd',
'e4a81c6a-0f7b-51ec-bfa7-1740c29a5705','28290012-2af5-5ae0-8195-1b405caa228f']
assert len(deleted)==len(set(deleted)) and all(u in c.by_id for u in deleted)
poses=[('R1304',[59.6,16.35],270),('R1305',[58.725,19.75],90),('R402',[60.45,19.75],270),('R404',[62.2,16.3],-90),('R1307',[59.25,22.25],0)]
translations=[]
for ref,pos,angle in poses:
 f=next(f for f in c.footprints if f.GetReference()==ref);orig=list(xy(f.GetPosition()))
 translations.append(dict(reference=ref,from_mm=orig,delta_mm=[round(pos[i]-orig[i],6) for i in range(2)],rotation_deg=angle))
def route(net,layer,pts,w=.2):return dict(net=net,layer=layer,width_mm=w,points_mm=pts)
plan=dict(revision='R190A',board_sha256=c.sha,scope=__doc__,translations=translations,delete_copper=deleted,
 deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
 reassign_vias=[dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),net=n,reason=reason) for u,n,reason in [
 ('5cc2b6b0-e919-4910-b0af-8902a95393d9','/HEAD_6V_RAW','Reuse the released wheel transfer without drilling a new hole or moving any GND hole.'),
 ('a58c8b39-ab39-41d2-a502-f26fa84ff045',wheel,'Restore wheel output using the former OV transfer; OV is restored through its other original vias.')]],
 routes=[
 route('/HEAD_6V_RAW','B.Cu',[[59.6,17.175],[59.6,18.125]]),
 route(middle,'B.Cu',[[59.6,15.675],[59.225,15.675],[58.725,16.175],[58.725,18.925]]),
 route(lower,'B.Cu',[[58.725,20.575],[58.3,21.0],[57.725,21.0]]),
 route(wheel,'B.Cu',[[60.45,18.925],[61.0,18.375],[61.0,17.45],[60.55,17.0]]),
 route(wheel,'In2.Cu',[[58.475,16.9],[60.45,16.9],[60.55,17.0]]),
 route(bus,'B.Cu',[[60.45,20.575],[60.45,21.1],[62.05,22.7],[62.4,22.7]]),
 route(bus,'B.Cu',[[62.2,15.475],[61.95,15.225],[61.1,15.225],[60.55,15.775]]),
 route(ov,'B.Cu',[[60.075,22.25],[60.25,22.25],[61.0,23.0]]),
 route(ov,'F.Cu',[[57.375,18.9],[58.9,18.9],[59.075,19.075]]),
 route('GND','B.Cu',[[62.2,17.125],[62.2,18.5],[62.4,18.7]],.3),
 route('GND','B.Cu',[[58.425,22.25],[58.425,21.925],[59.0,21.35],[59.575,21.3]],.3)],
 vias=[])
with out.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(dict(moved_parts=5,reassigned_vias=2,retired_segments=len(deleted),new_segments=sum(len(r['points_mm'])-1 for r in plan['routes']),adopted=False)))
