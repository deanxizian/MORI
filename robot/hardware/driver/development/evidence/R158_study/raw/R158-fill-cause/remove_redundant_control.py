import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
p=Path(sys.argv[1]);c=Copper(p);v=c.by_id['9fc6be27-25b2-4bce-8f44-98f39ccd1aa1'];assert v.GetNetname()=='MOTION_3V3';assert via_contact_layers(c.board,v)==['In3.Cu'];c.board.Remove(v);pcb.SaveBoard(str(p),c.board)
