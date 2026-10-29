"""Independent joint detector/clamp candidate with explicit local copper restoration.

This is unfinished: new OV, FAULT, HEAD_UV_N and bias-enable transfers still
need connection to their existing groups. No adoption or manufacturing release.
D1803 remains the original B340LA SMA part; D1802 is the separate TVS.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_snapshot
b=Path('robot/.state/c3-completion/trials');out=b/'R161A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
fs={f.GetReference():f for f in c.footprints};byid={uid(t):t for t in c.tracks}
pair=json.loads((b/'R161-bias-pair-v2.json').read_text())['best_pairs'][0]
poses={'U1301':([67.8,23.4],90),'D1803':([64.4,21.3],90),
 'C1303':([68.6,19.5],90),'C1302':([67.0,19.5],90),'C1301':([68.9,28.5],-90)}
for row in pair['poses']:poses[row['reference']]=(row['position_mm'],row['rotation_deg'])
trans=[]
for ref,(pos,angle) in poses.items():
 old=xy(fs[ref].GetPosition());row={'reference':ref,'from_mm':list(old),'delta_mm':[round(pos[i]-old[i],6) for i in range(2)],'rotation_deg':angle}
 if ref=='U1301':row['reconstruct_fixed_via_guards']=True
 trans.append(row)
p={'revision':'R161A','board_sha256':c.sha,'scope':__doc__,'translations':trans,'delete_copper':[],
 'deleted_copper_expected':{},'routes':[],'vias':[],'move_vias':[],'remove_obsolete_vias':[],
 'adoption_prohibited_until_complete_verification':True}
delete={
 '4a8d7b35-3b4b-4c24-a53f-f414b78f9d61',
 '2233b7b0-a172-414b-b05b-4bb9a08a453e','57330cbe-4127-4b66-8cbc-91bd347df963','68337903-98f5-4e4f-9ed8-5117238ed520','e6b35010-fab4-43b6-998f-221ea3ad499d',
 '7d202a1c-9df5-4dc1-9c35-040935191fb9','836b7b34-1a59-4e54-a08c-4046578ad1d4',
 '1d00a598-3b04-40c7-b57e-70f57a198633','3cf3a21c-1b8f-49d6-94a8-de64eb586516','456aaae9-abd5-4b9a-9f88-16fd9bca73ad','9520737d-3fad-4991-944c-1009c6173fc6','a7d4f9d0-f3b2-4bf2-9303-a7575ab9c1d7','aa0ebf82-8263-4f37-a03c-ce560632b896','ebd62011-a6f3-407e-b3b3-0ebc3e8e5392','f7add7b4-918d-485d-87ae-21c6f0c04568','fa93d558-a873-4f6a-99ff-327f65b38c83',
 '4096ad0d-74f9-477d-92d0-d0d7e2fff356','56034b58-b97f-468c-8f8b-1fac2a3a724f','bc8b83c4-d9b5-4be7-8ccd-c346eaaca4ff',
 'b4ef6c8e-58ee-4bb0-a41e-15e6f25db318','fcade418-13ee-4ae4-bad4-7a6aeafcf1aa','f556a927-d747-489f-a89c-c97db2181d02','01545c64-2a38-466e-aab5-3311a7972327','b5ea458b-8f13-4fc1-af11-4e066cb85117',
 '785f917d-97ad-40e6-86aa-aab0fb545610','29babd0c-55ef-42a3-8843-dd80ccac3c80','823c0a50-334b-4c56-af7f-de028d3d14d4',
 'e98846d3-b83f-4b32-8ed0-bad29883064e','62082821-1f25-4f46-bea7-5e4a836b0b07',
 '400071c8-db07-41c0-9e4e-8d2d15d5e57b','586926b4-93f6-4f54-929b-7781ab7ee7d9','b2909eee-2eec-445e-acf1-476a88d3a25a',
 '9466a214-ecd8-4661-b06b-384e4b46a1d8'}
uv='Net-(U1301-INA+_{slash}_UV)';ov='Net-(U1301-INB-_{slash}_OV)';uvn='/13 {slash} Head_Fault_Delay/HEAD_UV_N';ov1501='Net-(U1501-INB-_{slash}_OV)'
for t in c.segments:
 if t.GetNetname()==uv and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])<55:delete.add(uid(t))
for id_ in sorted(delete):
 t=byid[id_];assert isinstance(t,pcb.PCB_TRACK)
 p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for id_,pos,reason in [
 ('b7a4befe-1ae6-40bc-a958-e0a34a8c803c',[63.1,26.0],'Move the UV transfer away from the new 0.8 mm wheel-clamp via while restoring the same R1303 and R1302 input net.'),
 ('7bd5c3f2-f767-42af-b113-c3a4bc91e615',[67.4,30.0],'Keep all three U1501 OV transfer layers and restore its original R1503/R1504 network outside the relocated C1301 pads.'),
 ('fe2d0371-b479-48d2-a727-17898dd668f7',[65.3,25.3],'Keep the R1502-R1503 divider node and both outer-layer connections while making room for the detector OV transfer.')]:
 p['move_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,byid[id_]),'position_mm':pos,'reason':reason})
for id_ in ['45a1d39e-cb5b-4ef8-b13d-fe20aed2dfaf','fc152bf4-fbba-444c-ae12-f971486b6063','c2efb4d1-237c-4555-a92a-581a184c8584']:
 v=byid[id_];contacts=via_contact_layers(c.board,v,delete);assert contacts==[],(id_,contacts)
 p['remove_obsolete_vias'].append({'uuid':id_,'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':contacts,
  'reason':'The complete old left-side UV-only branch is replaced after both the detector and its filter move. All source attached tracks are explicitly removed; the R1302/R1303 net remains on its retained right-side branch. No ground or power transfer is removed.'})
def via(net,pos,diam=.5,drill=.3):p['vias'].append({'net':net,'position_mm':pos,'diameter_mm':diam,'drill_mm':drill})
for pos in [[62.875,24.4],[62.55,16.9]]:via('/WHEEL_VM',pos,.8,.4)
for net,pos in [('MOTION_3V3',[68.95,17.7]),(ov,[66.125,25.3]),(uv,[67.85,25.7]),('/FAULT_N',[69.35,21.2]),(uvn,[69.4,25.8]),(uvn,[44.6,28.75]),('/HEAD_UV_ENABLE',[60.55,17.95])]:via(net,pos)
def route(net,layer,width,pts):p['routes'].append({'net':net,'layer':layer,'width_mm':width,'points_mm':pts})
route('/WHEEL_VM','B.Cu',.8,[[64.4,23.3],[64.4,23.95],[64.1,24.25],[63.025,24.25],[62.875,24.4]])
route('/WHEEL_VM','B.Cu',.8,[[65.25,16.15],[65.25,17.3],[63.25,17.3],[62.85,16.9],[62.55,16.9]])
route('MOTION_3V3','B.Cu',.2,[[68.95,17.7],[69.4,18.15],[69.4,20.275],[68.6,20.275]])
route('MOTION_3V3','B.Cu',.2,[[68.6,20.275],[68.6,21.0],[67.8,21.8],[67.8,22.2625]])
route(ov,'B.Cu',.2,[[67.0,20.275],[67.0,20.95],[66.85,21.1],[66.85,22.2625]])
route(ov,'B.Cu',.2,[[66.85,21.4],[66.1,21.4],[66.1,25.275],[66.125,25.3]])
route(uv,'B.Cu',.2,[[61.575,25.25],[62.35,25.25],[63.1,26.0]])
route(uv,'In3.Cu',.2,[[63.1,26.0],[64.85,27.75],[65.25,27.75]])
route(uv,'B.Cu',.2,[[66.85,24.5375],[66.85,25.1],[67.45,25.7],[67.85,25.7]])
route(uv,'In3.Cu',.2,[[67.85,25.7],[67.85,26.2],[66.3,27.75],[65.25,27.75]])
route(uv,'F.Cu',.2,[[68.9,27.725],[68.45,27.275],[68.45,26.3],[67.85,25.7]])
route('/FAULT_N','B.Cu',.2,[[68.75,22.2625],[68.75,21.8],[69.35,21.2]])
route(uvn,'B.Cu',.2,[[68.75,24.5375],[68.75,25.15],[69.4,25.8]])
route('Net-(R1502-~-Pad1)','B.Cu',.2,[[64.75,26.175],[64.75,25.85],[65.3,25.3]])
route('Net-(R1502-~-Pad1)','F.Cu',.2,[[65.3,25.3],[65.75,25.75],[65.75,27.175]])
route(ov1501,'F.Cu',.2,[[65.75,28.825],[66.2,29.275],[66.675,29.275],[67.4,30.0]])
route(ov1501,'B.Cu',.2,[[68.575,28.5],[68.575,28.825],[67.4,30.0]])
route(ov1501,'In2.Cu',.2,[[67.4,30.0],[66.35,28.95],[65.525,28.95]])
route('Net-(R1311-~-Pad1)','B.Cu',.2,pair['common_node_route_B_mm'])
route('/HEAD_UV_ENABLE','B.Cu',.2,[[61.5,17.525],[60.975,17.525],[60.55,17.95]])
z=next(z for z in c.zones if uid(z)=='3174ce8f-0f53-4e28-82e5-fc19d056399b');patch=[[61.95,16.3],[64.7,16.3],[64.7,19.5],[61.95,19.5]]
added=polyset(z.Outline()).union(Polygon(patch)).area-polyset(z.Outline()).area
p['power_zone_expansions']=[{'uuid':uid(z),'source_expected':zone_snapshot(c.board,z),'union_patch_mm':patch,'expected_added_area_mm2':added,
 'reason':'Feed the existing D1802 TVS and relocated D1803 Schottky through two explicitly sized local wheel-power transfers while retaining 0.80 mm outer branches. Extend around, not through, the fixed J401 GND hole. Original plane priority, spacing, thermal and fill settings remain unchanged; all old supply-width/reference checks and transient/thermal review remain required.'}]
p['unfinished_connections']=[ov+'/new transfer to old divider', '/FAULT_N/new transfer to existing group',uvn+'/new to old output transfer','/HEAD_UV_ENABLE/new bias transfer to original group']
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R161A','transforms':len(trans),'replaced_tracks':len(delete),'new_routes':len(p['routes']),'new_vias':len(p['vias']),'removed_obsolete_UV_vias':len(p['remove_obsolete_vias']),'wheel_allocation_added_mm2':added}))
