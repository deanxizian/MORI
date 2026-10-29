"""Read-only R159H endpoint and placement inventory for the next joint layout study."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R160-source-inspection.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
fps=[]
for f in c.footprints:
 fps.append({'reference':f.GetReference(),'value':f.GetValue(),'library_id':str(f.GetFPID()),'position_mm':xy(f.GetPosition()),'rotation_deg':f.GetOrientationDegrees(),'layer':c.board.GetLayerName(f.GetLayer()),
  'pads':[{'name':c.pad_name(p),'uuid':uid(p),'position_mm':xy(p.GetPosition()),'size_mm':xy(p.GetSize()),'net':p.GetNetname()} for p in f.Pads()]})
reg=json.loads(Path('robot/hardware/driver/development/evidence/R159H/regression.json').read_text())
data={'board_sha256':c.sha,'footprints':fps,'placement_constraints':reg['critical_placement'],'In2_track_allow_list':sorted(in2_routing_nets(c.path))}
out.write_text(json.dumps(data,indent=2)+'\n')
selected={'U1001','U1301','U1302','Q1701','Q1301','U601','TH1501','C1503','D301','D302'}
for f in fps:
 if f['reference'] in selected:print(json.dumps(f))
print(json.dumps({'In2_allow_list':data['In2_track_allow_list']}))
