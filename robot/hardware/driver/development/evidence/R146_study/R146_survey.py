"""Read-only actuator switch group survey; no source PCB is saved."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
p=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(p); out=Path('robot/.state/c3-completion/trials/R146-survey.json');assert not out.exists()
assert c.sha=='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
refs=['U1601','Q1601','Q1602','C1601','C1602','C1603','D1601','D1602','R1601','R1602']
fs=[]
for f in c.footprints:
 if f.GetReference() not in refs:continue
 fs.append({'reference':f.GetReference(),'value':f.GetValue(),'position':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'layer':c.board.GetLayerName(f.GetLayer()),'pads':[{'pin':p.GetNumber(),'position':xy(p.GetPosition()),'net':p.GetNetname(),'size':xy(p.GetSize())} for p in f.Pads()]})
net='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
ts=[{'uuid':uid(t),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':t.GetWidth()/1e6,'layer':c.board.GetLayerName(t.GetLayer())} for t in c.segments if t.GetNetname()==net]
vs=[{'uuid':uid(v),'position':xy(v.GetPosition()),'diameter':v.GetWidth(pcb.F_Cu)/1e6,'drill':v.GetDrillValue()/1e6} for v in c.vias if v.GetNetname()==net]
gs=[{'pads':g['pads'],'layers':{ly:{'bounds':s.bounds,'area':s.area} for ly,s in g['layers'].items()}} for g in groups(c,net)]
r={'argv':[sys.executable,*sys.argv],'source_sha256':c.sha,'footprints':fs,'gate_tracks':ts,'gate_vias':vs,'gate_groups':gs}
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
assert hashlib.sha256(p.read_bytes()).hexdigest()==c.sha
