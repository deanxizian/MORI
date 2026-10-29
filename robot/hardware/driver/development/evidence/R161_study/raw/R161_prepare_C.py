"""Unfinished joint working board with local circuit restoration.

Keep both clamps and the complete existing wheel-power branch unchanged. Move
C1501 beside U1501 and put R1504 in its former place. All source ground vias,
mechanical interfaces, native rules and zone allocations are retained.
Long detector outputs, OV upstream, the UV divider and UV filter still need
complete routes and manufacturer-layout review. Never adopt this partial board.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
g=json.loads((b/'R161-Cgroup-v2.json').read_text());assert c.sha==g['source_sha256']
cap=json.loads((b/'R161-C1501-search.json').read_text())['best'][0]
fs={f.GetReference():f for f in c.footprints};byid={uid(t):t for t in c.tracks}
p={'revision':'R161C','scope':__doc__,'board_sha256':c.sha,'translations':[],
 'routes':[],'vias':[],'move_vias':[],'delete_copper':[],'deleted_copper_expected':{},
 'remove_obsolete_vias':[],'adoption_prohibited_until_complete_verification':True}
for r in g['placements']:
 ref=r['reference'];pos=r['position_mm'];ang=r['rotation_deg']
 if ref=='C1501':pos=cap['position_mm'];ang=cap['rotation_deg']
 old=list(xy(fs[ref].GetPosition()))
 row={'reference':ref,'from_mm':old,'delta_mm':[round(pos[i]-old[i],6) for i in range(2)],'rotation_deg':ang}
 if ref=='U1301':row.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True)
 p['translations'].append(row)
delete={
 '4a8d7b35-3b4b-4c24-a53f-f414b78f9d61',
 '2233b7b0-a172-414b-b05b-4bb9a08a453e','57330cbe-4127-4b66-8cbc-91bd347df963','68337903-98f5-4e4f-9ed8-5117238ed520','e6b35010-fab4-43b6-998f-221ea3ad499d',
 '7d202a1c-9df5-4dc1-9c35-040935191fb9','836b7b34-1a59-4e54-a08c-4046578ad1d4',
 '4096ad0d-74f9-477d-92d0-d0d7e2fff356','56034b58-b97f-468c-8f8b-1fac2a3a724f','bc8b83c4-d9b5-4be7-8ccd-c346eaaca4ff',
 '9466a214-ecd8-4661-b06b-384e4b46a1d8',
 'd994b9d8-51cd-57ab-9726-675ece8b8ff4','7a4650b4-1dc9-5ff9-af73-2ad3564d32de','5c71492c-4a1e-5185-a73f-b9991395ff02',
 'b4ef6c8e-58ee-4bb0-a41e-15e6f25db318','fcade418-13ee-4ae4-bad4-7a6aeafcf1aa',
 'f556a927-d747-489f-a89c-c97db2181d02','97d26239-9dbe-408c-96cb-e552d5dae574','06666dfa-0de5-402c-bae2-bc05c666dd08',
 'f9fbb5bd-dda9-49b0-b49a-3bedfd0eb994','08181aa8-ba08-4f54-bf08-f96b5ec78ef3'}
uv='Net-(U1301-INA+_{slash}_UV)';ov='Net-(U1301-INB-_{slash}_OV)';uvn='/13 {slash} Head_Fault_Delay/HEAD_UV_N'
ov1501='Net-(U1501-INB-_{slash}_OV)';mid='Net-(R1502-~-Pad1)';upper='Net-(R1501-~-Pad1)'
for t in c.segments:
 net=t.GetNetname();ln=c.board.GetLayerName(t.GetLayer())
 if net==uv and uid(t) not in ['e98846d3-b83f-4b32-8ed0-bad29883064e','bd8f22fb-09ad-4401-8676-f08c426f39e0']:delete.add(uid(t))
 if net==ov and (ln=='In3.Cu' or uid(t)=='e0595101-3239-45dd-ad6c-30d07a9fad40'):delete.add(uid(t))
 if net in [mid,upper] or (net==ov1501 and ln=='In2.Cu'):delete.add(uid(t))
for ident in sorted(delete):
 t=byid[ident];assert isinstance(t,pcb.PCB_TRACK) and t.GetNetname()!='/WHEEL_VM'
 p['delete_copper'].append(ident);p['deleted_copper_expected'][ident]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for ident,pos,reason in [
 ('4235992b-10c1-49b9-b6d7-b3df51cada3c',[67.8,25.55],'Retain the detector OV transfer identity outside the new U1301 body; the upstream detector connection remains unfinished.'),
 ('7bd5c3f2-f767-42af-b113-c3a4bc91e615',[66.5,29.65],'Restore R1503 on F and the existing U1501 OV network on In2 outside the relocated UV capacitor.'),
 ('ed145f08-9ec4-48e7-acaf-aabdac5dea88',[64.2,31.5],'Restore the original In2/In3/B OV bridge outside relocated R1502.'),
 ('fcd6ec6b-0145-4092-9c84-0765c014a1fa',[64.2,32.85],'Restore the original B/In3 OV bridge outside relocated R1502.'),
 ('fe2d0371-b479-48d2-a727-17898dd668f7',[67.6,28.5],'Restore R1503 F input and relocate its signal transfer outside the detector input/UV-filter region.'),
 ('da2cdecc-acee-4e55-bfbf-62ae3ca0fb49',[69.15,26.15],'Retain both original power-plane connections while clearing the relocated detector decoupling capacitor; refill and all width checks still required.')]:
 p['move_vias'].append({'uuid':ident,'source_expected':via_snapshot(c.board,byid[ident]),'position_mm':pos,'reason':reason})
for ident in ['45a1d39e-cb5b-4ef8-b13d-fe20aed2dfaf','fc152bf4-fbba-444c-ae12-f971486b6063','c2efb4d1-237c-4555-a92a-581a184c8584']:
 v=byid[ident];contacts=via_contact_layers(c.board,v,delete);assert contacts==[]
 p['remove_obsolete_vias'].append({'uuid':ident,'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':contacts,
  'reason':'Explicitly retire the isolated old left UV-only branch after the detector and its capacitor move. This working board leaves the replacement UV divider/filter unfinished, so it is prohibited from adoption. No power or ground transfer is removed.'})
for net,pos in [(mid,[63.85,30.6]),(uvn,[63.85,29.85])]:p['vias'].append({'net':net,'position_mm':pos,'diameter_mm':.5,'drill_mm':.3})
def route(net,layer,pts,width=.2):p['routes'].append({'net':net,'layer':layer,'width_mm':width,'points_mm':pts})
route('GND','B.Cu',[[64.0625,27.9],[63.65,27.9],[63.05,27.3],[62,27.3]],.3)
route('GND','B.Cu',[[62.2,17.125],[62.2,17.4],[61.6,18.0],[60.325,18.0]],.3)
route('MOTION_3V3','B.Cu',[[66.3375,27.9],[67.15,27.9],[67.15,27.6],[68.25,26.5],[68.8,26.5],[68.8,27.125]])
route('MOTION_3V3','B.Cu',[[69.15,26.15],[68.8,26.5]])
route(ov,'B.Cu',[[68.8,25.025],[68.8,25.25],[67.1,26.95],[66.3375,26.95]])
route(ov,'B.Cu',[[67.8,25.55],[67.8,26.25]])
route(uv,'B.Cu',[[62.75,25.25],[62.75,25.875],[63.4,26.525],[63.4,26.95],[64.0625,26.95]])
route(uvn,'B.Cu',[[64.0625,28.85],[63.35,28.85],[63.35,29.35],[63.85,29.85]])
route('Net-(R1311-~-Pad1)','B.Cu',[[42.9,24.325],[42.9,24.9],[43.35,25.35],[43.35,26.075]])
route(upper,'B.Cu',[[62.9,31.975],[62.9,32.65],[63.325,33.075],[63.325,33.5]])
route(mid,'B.Cu',[[62.9,30.325],[63.55,30.325],[63.85,30.6]])
route(mid,'In3.Cu',[[63.85,30.6],[65.0,30.6],[65.0,28.5],[67.6,28.5]])
route(mid,'F.Cu',[[67.6,28.5],[66.275,27.175],[65.75,27.175]])
route(ov1501,'F.Cu',[[65.75,28.825],[66.5,29.65]])
route(ov1501,'In2.Cu',[[66.5,29.65],[66.0,29.15],[64.8,29.15],[64.8,30.9],[64.2,31.5]])
route(ov1501,'B.Cu',[[64.2,31.5],[64.2,32.85]])
route(ov1501,'In3.Cu',[[62.0,31.4],[64.1,31.4],[64.2,31.5]])
route(ov1501,'In3.Cu',[[64.2,32.85],[63.75,33.3],[62.4,33.3]])
route(ov1501,'B.Cu',[[round(v,6) for v in pt] for pt in cap['route_B_mm']])
p['unfinished_connections']=['U1301 FAULT output to existing FAULT group','HEAD_UV_N new transfer to retained left output group',
 'R1311 HEAD_UV_ENABLE to original enable group','U1301 OV/new local C1302 to upstream R1306/R1307',
 'UV divider R1302 to R1303/U1301 group','C1301 filter at the actual U1301 UV input: no long detour accepted']
out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R161C','translations':len(p['translations']),'replaced_tracks':len(delete),'routes':len(p['routes']),
 'moved_non_ground_vias':len(p['move_vias']),'new_vias':len(p['vias']),'clamp_and_wheel_branch_preserved':True}))
