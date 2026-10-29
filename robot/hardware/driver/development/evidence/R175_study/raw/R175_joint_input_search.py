"""Search both current-sense input links after explicit neighbouring retirement.

The WHEEL_VM sample branch must be rebuilt and checked before any adoption.
These are sequential proposals, not accepted electrical connectivity.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_followup_search.py').read_text()
src=src.replace("rev+'-R175-followup'", "rev+'-R175-joint-input'")
start=src.index('src=src[:start]+"tasks=');end=src.index('\nold=',start)
src=src[:start]+'''src=src[:start]+"tasks=[('ina_input_plus','R1706.2','U1701.1'),('other_sense_input','R1703.2','U1702.3'),('wheel_sample_pair','R1707.1','R1702.1')]"+src[end:]'''+src[end:]
exec(compile(src,str(__file__),'exec'))
