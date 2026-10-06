"""Reuse native check pipeline with isolated P5R4 paths and P5R3 comparison."""
import sys, runpy
import all_trace_review_P5R3 as previous
from review_P5R4 import *
previous.paths, previous.source, previous.O, previous.KINDS = paths, source, O, KINDS
if sys.argv[1] == 'fill':
    for kind in sys.argv[2:] or KINDS:
        n, d, p, r = paths(kind)
        b = k.LoadBoard(str(p))
        tb = b.GetTitleBlock()
        tb.SetTitle(f'MORI {kind} / P5R4 / PROTOTYPE')
        tb.SetRevision('V1.2-H0.5-P5R4')
        tb.SetComment(0, 'Rear/IMU review corrections; bench tests NOT_TESTED')
        tb.SetComment(1, 'Review: hardware/v1_2/layout_P5R4/README.md')
        b.BuildConnectivity()
        k.ZONE_FILLER(b).Fill(b.Zones())
        k.SaveBoard(str(p), b)
        print(kind, 'filled', sha(p), flush=True)
else:
    runpy.run_path(str(H / 'tools/check_review_P5R3.py'), run_name='__main__')
