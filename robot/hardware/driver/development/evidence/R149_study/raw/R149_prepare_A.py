"""Independent U1001/CLR access trial; not a complete current-filter route or an adoption."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R149A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
p=dict(revision='R149A',scope=__doc__,board_sha256=c.sha,translations=[dict(reference='U1001',from_mm=[32.1,9.75],delta_mm=[0,.15])],delete_copper=[],deleted_copper_expected={},routes=[],vias=[dict(net='/ACT_CURRENT_FILTERED',position_mm=[31.05,5.85],diameter_mm=.5,drill_mm=.3)],move_vias=[])
for u,pos in [('f11d1219-0eff-4595-98ff-3b9d7c86b417',[31.5,5.15]),('b0e9e724-c25e-46f4-98ca-d10f446a0a9c',[32.3,14.0])]:
    p['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,c.by_id[u]),position_mm=pos,reason='Joint U1001 escape and exact restoration of original CLR connectivity; all native fill/reference checks still required.'))
for u in ['b85c496d-7d43-42d7-8427-3f8f25903d06','dac061d1-9521-473f-99fc-039084fe4898','8c1a9520-5be3-4daa-b164-364f22068aa9','e5f20fb0-ca67-437e-92fd-97a9ca34a6ac','f6ea2fbd-62e1-4e5c-a0c9-0b1e435b4896','7533ae71-956c-4efe-ac7d-c871de81e3da','62df8b3a-2129-42e2-a8c9-0ba591e2c3d1','02fbde6f-9604-57dc-aa7b-1cef37a5936d','31f107fd-7484-598c-9d44-614e8227628e','ce2386fc-05d7-5560-93e4-f76da6905b4a']:
    t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
def route(net,layer,pts):p['routes'].append(dict(net=net,layer=layer,width_mm=.2,points_mm=pts))
route('/ACT_CURRENT_FILTERED','B.Cu',[[30.8,7.0375],[30.8,6.1],[31.05,5.85]])
route('/CLR_N','B.Cu',[[31.45,7.0375],[31.45,6.4],[31.85,6.0],[31.85,5.5],[31.5,5.15]])
route('/CLR_N','In2.Cu',[[31.5,5.15],[31.85,5.5],[31.85,6.4],[31.5,6.75],[30.95,6.75],[30.45,6.25],[26.6,6.25]])
route('/CLR_N','B.Cu',[[32.1,14.0],[32.3,14.0]])
route('/CLR_N','F.Cu',[[32.3,14.0],[35.05,14.0],[35.2,13.85]])
route('/CLR_N','In3.Cu',[[32.3,13.0],[32.3,14.0]])
route('Net-(D1001-K)','B.Cu',[[33.4,13.3625],[33.4,13.65],[34.5,14.75],[35.75,14.75]])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
