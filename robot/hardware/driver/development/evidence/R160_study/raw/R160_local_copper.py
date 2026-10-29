"""Read-only exact copper inventory of the joint detector/divider work region."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R160-local-copper.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
nets={'Net-(U1301-INB-_{slash}_OV)','Net-(U1301-INA+_{slash}_UV)','Net-(U1501-INB-_{slash}_OV)','Net-(R1502-~-Pad1)','Net-(R1501-~-Pad1)','/13 {slash} Head_Fault_Delay/HEAD_UV_N'}
rows=[]
for t in c.tracks:
 points=[xy(t.GetPosition())] if isinstance(t,pcb.PCB_VIA) else [xy(t.GetStart()),xy(t.GetEnd())]
 local=any(58<=x<=70 and 20<=y<=34 for x,y in points)
 if t.GetNetname() not in nets and not local:continue
 rows.append({'uuid':uid(t),'net':t.GetNetname(),'points_mm':points,
  **({'kind':'via','snapshot':via_snapshot(c.board,t),'contact_layers':via_contact_layers(c.board,t)} if isinstance(t,pcb.PCB_VIA) else {'kind':'track','layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6})})
data={'scope':__doc__,'source_sha256':c.sha,'items':rows,'ground_vias_in_region':[{'uuid':r['uuid'],'position_mm':r['points_mm'][0]} for r in rows if r['kind']=='via' and r['net']=='GND']}
out.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'items':len(rows),'ground_vias_in_region':data['ground_vias_in_region']}))
