"""Power/motion follow-up review; P5R3 immutable, P5R4 rear/IMU untouched."""
from review_P5R3 import *
import review_P5R3 as base
O=H/'layout_P5R5';KINDS=['motion','power']
O.mkdir(exist_ok=True)
def paths(kind):
    assert kind in KINDS
    n=f'MORI_{kind}_P5R5';d=H/'kicad'/n;r=O/'reports'/kind
    r.mkdir(parents=True,exist_ok=True)
    return n,d,d/(n+'.kicad_pcb'),r
def source(kind):
    n=f'MORI_{kind}_P5R3';d=H/'kicad'/n
    return n,d,d/(n+'.kicad_pcb')
base.paths,base.source,base.O,base.KINDS=paths,source,O,KINDS
if __name__=='__main__'and sys.argv[1]=='init':base.init()
