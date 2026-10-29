"""Record why two proposed local transfers cannot be inserted into G.
This is a limited read-only native-geometry query, not a complete DRC check.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R162G-local-constraints.json';assert not out.exists()
c=Copper(str(b/'R162G/MORI_Interface_C3.kicad_pcb'));rows=[]
for pos in [(59.1,29.5),(59.3,30.7)]:
 point=Point(pos)
 pads=[{'pad':c.pad_name(c.by_id[u]),'layer':ly,'centre_to_land_mm':point.distance(s)} for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD) and point.distance(s)<.46]
 guards=[{'name':k['name'],'uuid':k['id'],'layers':k['layers']} for k in c.keepouts if k['vias'] and k['shape'].distance(point)<.252]
 nearby=sorted((point.distance(Point(xy(v.GetPosition()))),xy(v.GetPosition())) for v in c.vias if v.GetNetname()=='GND')[:2]
 rows.append({'proposed_position_mm':pos,'nearby_pad_conflicts':pads,'native_via_guards':guards,'nearest_GND_vias':nearby,'accepted':False})
v=c.by_id['3e277283-77ad-410b-88b3-66a442ebc866']
tracks=[]
for u in ['c0905f41-23fe-4cba-9c6d-1a0941c977f8','e0d0eccd-82da-409f-b3fe-f43c7ed5e8e9','010030bb-4392-4fef-a869-afa4bbcdc184','607568c6-08da-4925-96c8-a4527d56edbc']:
 t=c.by_id[u];tracks.append({'uuid':u,'net':t.GetNetname(),'width_mm':t.GetWidth()/1e6,'layer':c.board.GetLayerName(t.GetLayer()),'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd())})
result={'scope':__doc__,'source_sha256':c.sha,'queried_positions':rows,'existing_HEAD_VM_transfer':via_snapshot(c.board,v),'related_tracks':tracks,'PCB_edited':False}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'queried':len(rows),'native_guard_conflicts':[len(r['native_via_guards']) for r in rows]}))
