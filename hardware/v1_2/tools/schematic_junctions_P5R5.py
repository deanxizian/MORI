"""Split ambiguous four-way bus junctions into two explicit T junctions.
Only native schematic wire geometry changes; exported netlist equivalence is gated later.
"""
from review_P5R5 import *
from functional_schematic import sexpr,encode
import uuid,collections
for kind in KINDS:
 n,d,p,r=paths(kind);s=d/(n+'.kicad_sch');root=sexpr(s.read_text());nodes=collections.defaultdict(list)
 def ends(v):return [tuple(map(float,q[1:]))for q in next(x for x in v if isinstance(x,list)and x[0]=='pts')[1:]]
 wires=[v for v in root if isinstance(v,list)and v[0]=='wire']
 for v in wires:
  for pt in ends(v):nodes[pt].append(v)
 def wire(a,z):return sexpr(f'(wire (pts (xy {a[0]} {a[1]}) (xy {z[0]} {z[1]})) (stroke (width 0.254) (type default)) (uuid {uuid.uuid4()}))')
 changes=[]
 for v,ws in nodes.items():
  if len(ws)!=4 and not (kind=='power'and v in [(330.2,398.78),(601.98,398.78)]and len(ws)==3):continue
  other=lambda w:next(x for x in ends(w)if x!=v)
  up=[w for w in ws if other(w)[0]==v[0]and other(w)[1]<v[1]-5.07]
  left=[w for w in ws if other(w)[1]==v[1]and other(w)[0]<v[0]-5.07]
  assert up and left,('manual review required',kind,v)
  u,l=up[0],left[0];a,z=other(u),other(l);t=(round(v[0]-2.54,4),v[1]);c=(v[0],round(v[1]-2.54,4));q=(t[0],c[1])
  root.remove(u);root.remove(l)
  root.extend([wire(a,c),wire(c,q),wire(q,t),wire(z,t),wire(t,v),sexpr(f'(junction (at {t[0]} {t[1]}) (diameter 0.762) (color 0 0 0 0) (uuid {uuid.uuid4()}))')])
  changes.append(dict(original_junction_mm=v,additional_T_mm=t))
 s.write_text('('+root[0]+'\n'+'\n'.join(encode(v)if isinstance(v,list)else v for v in root[1:])+'\n)\n')
 dump(r/'schematic_T_junctions.json',json.loads((r/'schematic_T_junctions.json').read_text())+changes if (r/'schematic_T_junctions.json').exists()else changes);print(kind,'junctions split',len(changes))
