"""Form mutually compatible divider/filter pairs, then build an explicit prep plan.

This does not claim restored circuits or complete routability. Native validation
and all original connections/power/ground must still pass before adoption.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.ops import polygonize
from shapely.affinity import rotate,translate
from shapely.geometry import box
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');data=json.loads((b/'R186-four-part-pose-screen.json').read_text());out=b/'R186-swap-pairs.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert data['source_sha256']==c.sha
for path,name in [(b/'R138_joint_search.py','fab'),(b/'R167_joint_pose_screen.py','outline')]:
 node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'))
refs=set(data['poses']);fps={f.GetReference():f for f in c.footprints};omitted=set(data['released_terminal_tracks'])|{uid(p) for ref in refs for p in fps[ref].Pads()}
fixed_body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.F_Cu and f.GetReference() not in refs])
fixed_guards=unary_union([k['shape'] for k in c.keepouts if k['tracks'] and 'F.Cu' in k['layers'] and not any(k['name'].startswith('BODY_'+ref+'_') for ref in refs)])
def geometry(ref,row):
 f=pcb.FOOTPRINT(fps[ref]);f.SetOrientationDegrees(row['rotation_deg']);f.SetPosition(pcb.VECTOR2I(*(round(v*1e6) for v in row['position_mm'])))
 return dict(row=row,body=fab(f),yard=outline(f,pcb.F_CrtYd),pads={p.GetNumber():(p.GetNetname(),shape(p,pcb.F_Cu),xy(p.GetPosition())) for p in f.Pads()})
geometries={r:[geometry(r,row) for row in data['poses'][r]] for r in refs}
def path(a,z,aa,zz):
 def escape(p,centre):
  dx,dy=p[0]-centre[0],p[1]-centre[1];d=math.hypot(dx,dy);return (p[0]+.3*dx/d,p[1]+.3*dy/d)
 a1=escape(a,aa);z1=escape(z,zz);dx,dy=z1[0]-a1[0],z1[1]-a1[1];m=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
 for mid in [(a1[0]+sx*m,a1[1]+sy*m),(z1[0]-sx*m,z1[1]-sy*m)]:
  pts=[a,a1]
  if math.dist(a1,mid)>1e-8 and math.dist(mid,z1)>1e-8:pts.append(mid)
  pts.extend([z1,z]);yield pts
pairs={}
for first,last,net in [('R1702','R1703','Net-(R1702-~-Pad2)'),('R1102','C1102','/ACT_CURRENT_FILTERED')]:
 fixed_copper=unary_union([s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and u not in omitted and c.by_id[u].GetNetname()!=net])
 valid=[]
 for a in geometries[first]:
  for z in geometries[last]:
   if a['yard'].intersection(z['yard']).area>1e-8:continue
   if any(p[1].distance(q[1])<.2-1e-6 for p in a['pads'].values() for q in z['pads'].values()):continue
   if math.dist(a['pads']['2'][2],z['pads']['1'][2])>4:continue
   lands=unary_union([p[1] for g in [a,z] for p in g['pads'].values() if p[0]==net])
   foreign=unary_union([fixed_copper]+[p[1] for g in [a,z] for p in g['pads'].values() if p[0]!=net])
   bodies=fixed_body.union(a['body']).union(z['body'])
   best=[]
   for pts in path(a['pads']['2'][2],z['pads']['1'][2],a['row']['position_mm'],z['row']['position_mm']):
    line=LineString(pts);stroke=line.buffer(.1)
    if foreign.distance(line)<.305 or stroke.intersects(fixed_guards) or stroke.difference(lands).intersection(bodies).area>1e-8:continue
    if line.length>5:continue
    best.append((line.length,pts))
   if not best:continue
   length,points=min(best)
   endpoint_target=(58.8,16.3875) if first=='R1702' else (30.8,6.8875)
   score=length+math.dist(z['pads']['2' if first=='R1702' else '1'][2],endpoint_target)
   valid.append(dict(first=a['row'],last=z['row'],net=net,points_mm=[[round(v,6) for v in p] for p in points],length_mm=length,score=score))
 valid.sort(key=lambda r:r['score']);pairs[first+'_'+last]=valid
 print(first,last,'complete pair geometries',len(valid),'best',valid[:1],flush=True)
result=dict(scope=__doc__,source_sha256=c.sha,pairs=pairs,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
if all(pairs.values()):
 chosen=[v[0] for v in pairs.values()];moves=[];routes=[]
 for (first,last),pair in zip([('R1702','R1703'),('R1102','C1102')],chosen):
  for ref,key in [(first,'first'),(last,'last')]:
   row=pair[key];moves.append(dict(reference=ref,from_mm=list(xy(fps[ref].GetPosition())),delta_mm=row['delta_mm'],rotation_deg=row['rotation_deg'],reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True,repartition_fixed_via_guards=True))
  routes.append(dict(net=pair['net'],layer='F.Cu',width_mm=.2,points_mm=pair['points_mm']))
 deleted=data['released_terminal_tracks']
 plan=dict(revision='R186B',board_sha256=c.sha,scope=__doc__,translations=moves,delete_copper=deleted,
           deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},routes=routes)
 target=b/'R186B-plan.json';assert not target.exists();target.write_text(json.dumps(plan,indent=2)+'\n')
