"""Native checks for P5R6 candidates only; no manufacturing data."""
import sys
import runpy
import all_trace_review_P5R3 as previous
from review_P5R6 import *

previous.paths, previous.source = paths, source
previous.O, previous.KINDS = O, KINDS
if sys.argv[1] == 'fill':
    for kind in sys.argv[2:] or KINDS:
        n, d, p, r = paths(kind)
        b = k.LoadBoard(str(p))
        tb = b.GetTitleBlock()
        tb.SetTitle(f'MORI {kind} / P5R6 / PROTOTYPE')
        tb.SetRevision('V1.2-H0.5-P5R6')
        tb.SetComment(0, 'Footprint / bootstrap / marking review; bench NOT_TESTED')
        tb.SetComment(1, 'Review: hardware/v1_2/layout_P5R6/README.md')
        b.BuildConnectivity()
        k.ZONE_FILLER(b).Fill(b.Zones())
        k.SaveBoard(str(p), b)
        print(kind, 'filled', sha(p), flush=True)
else:
    runpy.run_path(str(H / 'tools/check_review_P5R3.py'), run_name='__main__')
