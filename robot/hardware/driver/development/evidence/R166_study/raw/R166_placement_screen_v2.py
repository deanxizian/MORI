"""Extend the pose screen with native same-face courtyard polygons.

The R166C native rejection showed why nominal bodies and pad clearance alone
cannot qualify a placement. Reproduce that specific courtyard rejection, then
screen all compared poses again. Routing and through-via access remain separate.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R166_placement_screen.py').read_text().replace('R166-placement-screen.json','R166-placement-screen-v2.json')
old="refs=['Q1701','C1702'];fps="
new="""def courtyard(f):
 lines=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=pcb.B_CrtYd:continue
  a,z=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,z]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],z[0]),min(a[1],z[1]),max(a[0],z[0]),max(a[1],z[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(lines))))
"""+old
assert code.count(old)==1;code=code.replace(old,new)
old="other_body=unary_union([fab(f) for f in others])"
new=old+"""
other_courtyards=unary_union([courtyard(f) for f in others])
test=pcb.FOOTPRINT(source['Q1701']);test.SetOrientationDegrees(270);test.SetPosition(pcb.VECTOR2I(57000000,14250000))
assert courtyard(test).intersection(courtyard(fps['U402'])).area>1e-8, 'Native R166C courtyard rejection was not reproduced'
assert courtyard(source['Q1701']).intersection(courtyard(fps['U402'])).area<1e-8, 'Source must retain its original clearance'
"""
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("'body':0,'pad':0", "'body':0,'courtyard':0,'pad':0")
old="if body.intersection(other_body).area>1e-8:rejections[ref]['body']+=1;continue"
new=old+"\n    yard=courtyard(f)\n    if yard.intersection(other_courtyards).area>1e-8:rejections[ref]['courtyard']+=1;continue"
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace('body=body,pads=pp','body=body,courtyard=yard,pads=pp')
old="if q['body'].intersection(cap['body']).area>1e-8:continue"
new=old+"\n  if q['courtyard'].intersection(cap['courtyard']).area>1e-8:continue"
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("['body','pads','score']", "['body','courtyard','pads','score']")
code=code.replace("existing_leads_rerouted=False", "native_R166C_courtyard_rejection_reproduced=True,existing_leads_rerouted=False")
exec(compile(code,str(__file__),'exec'))
