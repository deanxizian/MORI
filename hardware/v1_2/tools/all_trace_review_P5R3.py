"""Use the audited P5R2 inventory/export implementation with isolated P5R3 paths."""
import all_trace_review_P5R2 as legacy
from review_P5R3 import paths, source, O
legacy.paths=paths;legacy.source=source;legacy.O=O
from all_trace_review_P5R2 import *
