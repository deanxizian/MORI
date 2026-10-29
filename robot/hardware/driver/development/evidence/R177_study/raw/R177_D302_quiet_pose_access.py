"""Compare native poses with new FAULT/CLR traces kept out of L701 projection.

This additional planning choice addresses the actual new CLR-under-inductor
overlap found in R177G. It is not a new native all-component keepout, nor an EMI
qualification. Existing copper and all source supply/reference checks remain.
"""
from pathlib import Path
import sys
b=Path('robot/.state/c3-completion/trials')
mode=sys.argv[1];assert mode in ['fault','clr']
src=(b/'R177_D302_pose_access.py').read_text()
replacements={
 "out=b/'R177-D302-pose-access.json'": "out=b/'R177-D302-quiet-"+mode+"-pose-access.json'",
 "net='/FAULT_N';free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)": "net="+repr('/FAULT_N' if mode=='fault' else '/CLR_N')+";free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)\ninductor=fab(next(o for o in c.footprints if o.GetReference()=='L701'))\nblocked=[g.union(inductor.buffer(.102)) for g in blocked]",
 "if 'Q1701.3' in g['pads']": "if "+repr('Q1701.3' if mode=='fault' else 'U303.2')+" in g['pads']",
 "land=actual['1'][1]": "land=actual["+repr('1' if mode=='fault' else '2')+"][1]",
 "optimistic_fault_access_cells": "optimistic_"+mode+"_access_cells",
 "with_optimistic_fault_access": "with_optimistic_"+mode+"_access",
 "scope=__doc__": "scope="+repr(__doc__),
}
for old,new in replacements.items():
 assert old in src,old
 src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))
