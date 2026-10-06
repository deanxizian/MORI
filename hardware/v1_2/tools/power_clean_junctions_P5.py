"""Replace remaining intersecting branches with deliberate local junctions."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b)
k.SaveBoard(str(r/'before_clean_junctions.kicad_pcb'),b)
remove=['500150b6','77217bd7','5b65d7aa','f33e40c2','f4fb80ed','997aa8ef',
        '1bdd793a','b1951129','96efc44b','3a61850a','5b69be50','5bb7990b']
deleted=[]
for t in list(b.GetTracks()):
    if any(t.m_Uuid.AsString().startswith(s)for s in remove):
        deleted.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),width_mm=k.ToMM(t.GetWidth())));b.Delete(t)
routes=[('/C5_EN',F,[(28.3464,38.3032),(28.3464,40.7416),(27.5336,40.7416)]),
 ('/+3V3',B,[(36.3474,16.9418),(36.779199,17.373599),(36.779199,20.32)]),
 ('/+5V_MOTION',F,[(8.475,25),(7.478,25.997),(7.478,29.978)])]
for net,l,ps in routes:
    assert all(Guard(b,net).line_clear(a,z,l,.2)for a,z in zip(ps,ps[1:])),(net,ps)
    track(b,net,ps,.2,l)
k.SaveBoard(str(p),b);(r/'clean_junctions.json').write_text(json.dumps(dict(deleted=deleted,routes=routes,load_note='Only redundant 0.2mm W_VM overlap removed; the original 1.5mm C10 feed remains. +5V testpoint branch relocated, 0.8mm load feed remains.'),indent=2)+'\n')
