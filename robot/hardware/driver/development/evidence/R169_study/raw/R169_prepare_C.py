"""Independent original-orientation comparison retiring only six LIMIT tracks.

This is a routing preparation, not adoption; the LIMIT connection must be fully
restored with its original resistor and explicit GND return retained. All part
poses, pads, vias, guard outlines, zones and rules remain the canonical source.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R169C-plan.json';assert not out.exists();c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
tt=[t for t in c.segments if t.GetNetname()=='Net-(U1701-LIMIT)'];assert len(tt)==6
p=dict(revision='R169C',scope=__doc__,board_sha256=c.sha,delete_copper=[uid(t) for t in tt],deleted_copper_expected={uid(t):dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd()))) for t in tt},routes=[],vias=[],adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n')
