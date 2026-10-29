"""Restore unchanged feed tracks released only for hypothetical via movement.

The selected H/I passive poses did not require four of the five provisional via
relocations. Keep old pad-terminal retirements and four obsolete right GND leads
explicit, while restoring other tracks released solely by the broad pose screen.
Native DRC/refill/regression, not this classification, determines acceptability.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170J-plan.json';assert not out.exists();p=json.loads((b/'R170I-plan.json').read_text());s=json.loads((b/'R170-cell-return-score.json').read_text());c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');refs={'R1701','C1701','R1706','R1707'};ids={uid(q) for f in c.footprints if f.GetReference() in refs for q in f.Pads()};keep={'5406aba7-c615-41a9-a6e9-192a3ed4d599','93815fe2-ca82-4388-8f2b-479a56ab871b','d61b3009-7a0d-55cf-ab70-1f6e60d2465c','dcb2b41a-82bd-47f9-9a25-09dbdf14ff28'};restore=[]
for u in s['prospectively_retired_tracks']:
 if u in keep:continue
 t=c.by_id[u];ly=c.board.GetLayerName(t.GetLayer());g=c.shapes[u,ly]
 if any(t.GetNetname()==c.by_id[z].GetNetname() and (z,ly) in c.shapes and g.intersects(c.shapes[z,ly]) for z in ids):continue
 restore.append(u);p['delete_copper'].remove(u);del p['deleted_copper_expected'][u]
p.update(revision='R170J',scope=__doc__,restored_original_tracks_after_pose_screen=restore);out.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps([dict(uuid=u,net=c.by_id[u].GetNetname(),a=xy(c.by_id[u].GetStart()),z=xy(c.by_id[u].GetEnd())) for u in restore]))
