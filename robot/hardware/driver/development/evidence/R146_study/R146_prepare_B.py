"""Rebuild the joint gate trial from canonical R145I after actual native failures."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R146B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R146A-plan.json').read_text());p['revision']='R146B';p['scope']='Independent joint gate/clamp layout trial with native collision feedback; Q1602 gate remains open. Not adopted.'
assert c.sha==p['board_sha256']
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE';src='/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE';m5='/01 {slash} Core/MOTION_5V';sense='Net-(U1001-S2{slash}_WHEEL_sense)'
# Obtain exact KiCad spelling from the source, not a guessed display label.
sense=c.by_id['e4b67b22-d32a-459b-8b55-989fcafd816c'].GetNetname()
remove=p['delete_copper']+['99ab00bb-6229-4bbd-bcab-fda844037095','5fb83ea2-603e-4b06-aaa4-799eaf73dfec','cc6103ad-8528-4530-bbd6-8c16d5c66ab0','e4b67b22-d32a-459b-8b55-989fcafd816c','8732ae58-53a6-4615-9655-125a06db4c8f','3db54abc-0af7-46b4-92b9-14094c693db8','23caad3a-a256-4835-b0a8-f9466105f55e','b422bd16-a21a-4191-afb2-6d6e4fa5b55e']
p['delete_copper']=remove;p['deleted_copper_expected']={}
for u in remove:
 t=c.by_id[u];p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['translations'][2]['delta_mm']=[0,.45]
p['move_vias']=[]
for u,point,why in [('10bdeb96-94ec-4dc6-beec-853f3cc22737',[39.25,17.35],'Retain gate resistor pad clearance and restore B/In3 tails.'),('c9ef7bb5-bef9-48b7-b4cf-23501fe0a859',[45.25,8.575],'Move outside translated Q1601 drain pads; restore full-width B/In2 connection and add a local GND return.')]:
 p['move_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'position_mm':point,'reason':why})
p['vias']=[{'net':n,'position_mm':v,'diameter_mm':.5,'drill_mm':.3} for n,v in [(gate,[38.05,12.2]),('GND',[45.45,6.85])]]
p['routes']=[]
def route(net,ly,w,points):p['routes'].append({'net':net,'layer':ly,'width_mm':w,'points_mm':points})
for y in [8.345,9.615,10.885]:route(src,'F.Cu',.6,[[38.2475,y],[38.8975,y]])
route('/UPS_BAT','B.Cu',.3,[[39.15,13],[38.97,13.18],[37.95,13.18]])
route(gate,'B.Cu',.2,[[38.6,16.525],[38.95,16.525],[39.25,16.825],[39.25,17.35]])
route(gate,'In3.Cu',.2,[[38.715,16.4],[39.25,16.935],[39.25,17.35]])
route('Net-(C1603-~-Pad1)','B.Cu',.2,[[38.6,18.175],[39.1,18.675],[39.1,20.3]])
route(gate,'F.Cu',.3,[[37.825,13.95],[37.825,13.3],[38.05,13.075],[38.05,12.2]])
route(gate,'F.Cu',.3,[[38.05,12.2],[38.095,12.155],[38.8975,12.155]])
route(gate,'B.Cu',.3,[[38.05,12.2],[37.6,12.2],[36.85,12.95],[36.85,15.25],[36.55,15.55]])
route('Net-(D1001-K)','B.Cu',.2,[[36.8,8.2125],[36.8,11.1],[36.35,11.55],[36.35,13.6625],[35.6,14.4125]])
route(sense,'F.Cu',.2,[[40.815,7.5],[45.6,7.5],[46.1,8],[46.1,8.85],[45.6,9.35]])
route(m5,'B.Cu',.4,[[44.5,6.4],[44.5,7.65],[45.25,8.4],[45.25,8.575]])
route(m5,'In2.Cu',.5,[[45.25,8.575],[45.25,9.5],[44.5,10.25]])
out.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'plan':str(out),'removed_tracks':len(remove),'routes':len(p['routes'])}))
