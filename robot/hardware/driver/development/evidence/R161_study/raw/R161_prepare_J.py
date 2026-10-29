"""Retire two complete dead transfer branches left by the explicit relocation.
All source terminal-to-terminal copper is retained. These tails now end at
unused transfer holes, after the old U1301/R1311 escapes were explicitly
removed in E. Replacement circuit links remain unfinished, preventing adoption.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161J-plan.json';assert not out.exists()
p=json.loads((b/'R161I-plan.json').read_text());p['revision']='R161J';p['scope']+='\n'+__doc__
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
ids=['45103aba-d39e-40aa-8d49-a3561158cb0e','46b2af7b-5664-4ddc-922b-482d7e85fa1f','e96be0e9-2209-45b0-bbfd-a0fdaca3d7cd','c327aae5-610d-4bfa-bac6-0b685880c8fb','e518cf78-8855-44fb-b1e4-749f134ebe36']
for u in ids:
 assert u not in p['delete_copper'];t=c.by_id[u];assert isinstance(t,pcb.PCB_TRACK)
 p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
for u in ['c56d70fa-8404-4e66-b4ea-0eb4f4ba7226','61f593f6-35ac-484f-8d2f-a7902a0a6d0e']:
 p['remove_obsolete_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,c.by_id[u]),'remaining_contact_layers':[],'reason':__doc__})
out.write_text(json.dumps(p,indent=2)+'\n');print(p['revision'])
