"""Joint input planning with existing connected groups for branch restoration.

Exact pad pairs remain mandatory for INA300 local inputs. Other branch targets
use their actual native copper group so a remote IC outside the local window
does not incorrectly become NO_ENDPOINT_ACCESS. No PCB is changed.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
loader=(b/'R175_followup_search.py').read_text()
loader=loader.replace("exec(compile(src,str(__file__),'exec'))", "(b/'R175_followup_expanded.py').write_text(src)")
exec(compile(loader,'expand_followup','exec'))
src=(b/'R175_followup_expanded.py').read_text()
src=src.replace("rev+'-R175-followup'", "rev+'-R175-inputs-branches'")
start=src.index('tasks=');end=src.index('\nrows=[]',start)
src=src[:start]+"tasks=[('ina_input_plus','R1706.2','U1701.1'),('ina_input_minus','R1707.2','U1701.2'),('other_sense_input','R1703.2','U1702.3'),('wheel_pair','R1707.1','R1702.1'),('wheel_restore','R1702.1','R1101.2')]"+src[end:]
old=" z=dict(pads=[bn],layers={ly:c.shapes[uid(bb),ly] for ly in p.layers if (uid(bb),ly) in c.shapes})"
new=old+"\n if name in ['other_sense_input','wheel_restore']:z=next(g for g in p.routing_groups(net) if bn in g['pads'])"
assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))
