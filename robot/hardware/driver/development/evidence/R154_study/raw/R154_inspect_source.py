"""Read current power/sense anchors and immutable source geometry for the next study."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
refs={'U1201','R1304','R1305','R1306','R1307','R1308','U1301','U1302','C1301','C1302','C1303','R901'}
r={'board_sha256':c.sha,'components':{},'RAW_pads':[],'RAW_vias':[],'RAW_tracks':[]}
for f in c.footprints:
 pads=[{'name':c.pad_name(p),'net':p.GetNetname(),'position_mm':xy(p.GetPosition()),'size_mm':xy(p.GetSize())} for p in f.Pads()]
 if f.GetReference() in refs:r['components'][f.GetReference()]={'value':f.GetValue(),'layer':c.board.GetLayerName(f.GetLayer()),'position_mm':xy(f.GetPosition()),'angle_deg':f.GetOrientationDegrees(),'pads':pads}
 r['RAW_pads'] += [p for p in pads if p['net']=='/HEAD_6V_RAW']
for v in c.vias:
 if v.GetNetname()=='/HEAD_6V_RAW':r['RAW_vias'].append({'uuid':uid(v),**via_snapshot(c.board,v)})
for t in c.segments:
 if t.GetNetname()=='/HEAD_6V_RAW':r['RAW_tracks'].append({'uuid':uid(t),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd())})
out=Path('robot/.state/c3-completion/trials/R154-source-geometry.json');assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
