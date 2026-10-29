"""Read-only native pad/body/via and adjacency screen of Q1701/C1702 poses.

These are geometry candidates, not routed/qualified placements. Existing leads
would need explicit reconstruction. No board or native rule is modified.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R166-placement-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
refs=['Q1701','C1702'];fps={f.GetReference():f for f in c.footprints};source={r:fps[r] for r in refs}
others=[f for f in c.footprints if f.GetReference() not in refs and f.GetLayer()==pcb.B_Cu]
other_body=unary_union([fab(f) for f in others])
excluded={uid(p) for r in refs for p in source[r].Pads()}
pads=[(c.pad_name(p),p.GetNetname(),c.shapes[uid(p),'B.Cu']) for p in c.pads if uid(p) not in excluded and (uid(p),'B.Cu') in c.shapes]
vias=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias if (uid(v),'B.Cu') in c.shapes])
u=next(p for p in c.pads if c.pad_name(p)=='U1702.5');up=xy(u.GetPosition())
rows={r:[] for r in refs};rejections={r:{'body':0,'pad':0,'via_pad':0,'bypass_distance':0} for r in refs}
for ref in refs:
 f0=source[ref];old=xy(f0.GetPosition());oldangle=f0.GetOrientationDegrees()
 for dx in [-1,-.75,-.5,-.25,0,.25,.5,.75,1]:
  for dy in [-1,-.75,-.5,-.25,0,.25,.5,.75,1]:
   for angle in [0,90,180,270]:
    f=pcb.FOOTPRINT(f0);f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round((old[0]+dx)*1e6),round((old[1]+dy)*1e6)))
    body=fab(f);pp=[(p.GetNumber(),p.GetNetname(),shape(p,pcb.B_Cu),xy(p.GetPosition())) for p in f.Pads()]
    if body.intersection(other_body).area>1e-8:rejections[ref]['body']+=1;continue
    if any(s.distance(vias)<.2-1e-6 for _,_,s,_ in pp):rejections[ref]['via_pad']+=1;continue
    hits=[name for _,net,s,_ in pp for name,othernet,os in pads if net!=othernet and s.distance(os)<.2-1e-6]
    if hits:rejections[ref]['pad']+=1;continue
    dist=math.dist(up,next(p[3] for p in pp if p[0]=='1')) if ref=='C1702' else None
    if dist is not None and dist>4+1e-9:rejections[ref]['bypass_distance']+=1;continue
    rotation_cost=min((angle-oldangle)%360,(oldangle-angle)%360)/180
    rows[ref].append(dict(reference=ref,position_mm=[old[0]+dx,old[1]+dy],rotation_deg=angle,delta_mm=[dx,dy],score=math.hypot(dx,dy)+rotation_cost,body=body,pads=pp,bypass_distance_mm=dist))
 print(ref,'individual_poses',len(rows[ref]),flush=True)
combos=[]
for q in rows['Q1701']:
 for cap in rows['C1702']:
  if q['body'].intersection(cap['body']).area>1e-8:continue
  if any(a[1]!=z[1] and a[2].distance(z[2])<.2-1e-6 for a in q['pads'] for z in cap['pads']):continue
  compact=lambda row:{k:v for k,v in row.items() if k not in ['body','pads','score']}
  combos.append(dict(Q1701=compact(q),C1702=compact(cap),score=q['score']+cap['score'],fault_pad_mm=list(next(p[3] for p in q['pads'] if p[0]=='3'))))
combos.sort(key=lambda x:x['score'])
pin_readback=[dict(pad=c.pad_name(p),net=p.GetNetname(),position_mm=list(xy(p.GetPosition())),face=c.board.GetLayerName(source['Q1701'].GetLayer())) for p in source['Q1701'].Pads()]
result=dict(scope=__doc__,source_sha256=c.sha,native_Q1701_pins=pin_readback,C1702_face=c.board.GetLayerName(source['C1702'].GetLayer()),U1702_face=c.board.GetLayerName(fps['U1702'].GetLayer()),individual_poses={r:len(v) for r,v in rows.items()},rejection_counts=rejections,combined_poses=combos,existing_leads_rerouted=False,native_DRC='NOT_TESTED',adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print('combined',len(combos),flush=True)
for angle in [0,90,180,270]:
 candidates=[x for x in combos if x['Q1701']['rotation_deg']==angle]
 print('Qangle',angle,'count',len(candidates),'best',candidates[:1],flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
