"""Finalize local polarity annotations and P5 title blocks; pin maps unchanged."""
import json,sys
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
from functional_schematic import sexpr,encode,q
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));connected(b)
if kind=='power':
    plugin=k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP)
    changed=[]
    for t in b.GetTracks():
        if t.m_Uuid.AsString()in ['196f80fa-e21f-4366-9b39-7bbaa4227271','3ae95368-2e5e-43e6-a75a-f2184f466547']:
            w=.6 if t.m_Uuid.AsString().startswith('196f') else 1.
            assert Guard(b,t.GetNetname()).line_clear(xy(t.GetStart()),xy(t.GetEnd()),t.GetLayer(),w)
            t.SetWidth(mm(w));changed.append([t.m_Uuid.AsString(),w])
    for f in b.GetFootprints():
        if f.GetReference()=='U40':
            for g in f.GraphicalItems():
                if g.m_Uuid.AsString()=='7b56c7da-6922-44a2-bc86-4130f8076ac8':g.Move(pt(.25,-1.18))
        if f.GetReference()=='J11':
            for g in f.GraphicalItems():
                if hasattr(g,'GetText')and g.GetText()=='+':g.SetPosition(pt(66,1.8))
        if f.GetReference()in['U40','J11']:plugin.FootprintSave(str(d/'footprints/MORI_Custom.pretty'),f)
    (r/'dump_load_necks.json').write_text(json.dumps(dict(changes=changed,scope='Drawn load widths corrected; pulsed/thermal qualification NOT_TESTED'),indent=2)+'\n')
title=b.GetTitleBlock();title.SetTitle('MORI '+kind+' / P5 / PROTOTYPE');title.SetRevision('V1.2-H0.5-P5');title.SetComment(0,'Fresh placement and routing; physical tests NOT_TESTED');title.SetComment(1,'Source rules and exceptions: hardware/v1_2/layout_P5/routing_acceptance.md');b.SetTitleBlock(title);k.SaveBoard(str(p),b)
sch=d/(name+'.kicad_sch');s=sexpr(sch.read_text());title=next(x for x in s if isinstance(x,list)and x[0]=='title_block')
title[:]=['title_block',['title',q('MORI / '+kind+' / P5 - FUNCTIONAL SCHEMATIC')],['date',q('2026-09-23')],['rev',q('V1.2-H0.5-P5')],['comment','1',q('PROTOTYPE / NOT_TESTED - circuit and pin assignments retained')]]
sch.write_text('('+s[0]+'\n'+'\n'.join(encode(x)if isinstance(x,list)else x for x in s[1:])+'\n)\n')
print(kind,'P5 annotations saved')
