"""Read-only four-passive comparison around the half-turned INA300 in R169D.

All source GND vias, fixed interfaces, other parts and original rules remain.
Only explicitly enumerated terminal tracks and five non-GND via positions are
prospectively released for this placement screen. Conflicts with those vias
are listed, not waived; all affected connections must be rebuilt and verified.
No board is saved and no routability, thermal or manufacturer claim is made.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
from shapely.affinity import translate,rotate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170-cell-extended-screen.json';assert not out.exists();c=Copper(b/'R169D/MORI_Interface_C3.kicad_pcb');fps={f.GetReference():f for f in c.footprints};refs=['R1701','C1701','R1706','R1707'];ids={uid(p) for ref in refs for p in fps[ref].Pads()};movepos={(46.3,11.85),(45.29,10.05),(44.575,10.125),(42.55,14.2),(52.45,11.875)};movable={uid(v):v for v in c.vias if xy(v.GetPosition()) in movepos};assert len(movable)==5 and all(v.GetNetname()!='GND' for v in movable.values());retired=set()
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer());g=c.shapes[uid(t),ly]
 if any(t.GetNetname()==c.by_id[u].GetNetname() and (u,ly) in c.shapes and g.intersects(c.shapes[u,ly]) for u in ids|set(movable)):retired.add(uid(t))
retired.update(['5406aba7-c615-41a9-a6e9-192a3ed4d599','93815fe2-ca82-4388-8f2b-479a56ab871b','d61b3009-7a0d-55cf-ab70-1f6e60d2465c','dcb2b41a-82bd-47f9-9a25-09dbdf14ff28'])
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
faces=['B.Cu','F.Cu'];fb={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference() not in refs]) for ly in faces};fy={ly:unary_union([outline(f,pcb.F_CrtYd if ly=='F.Cu' else pcb.B_CrtYd) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference() not in refs]) for ly in faces};vl={ly:unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PCB_VIA) and u not in movable]) for ly in faces};ts={ly:unary_union([c.shapes[uid(t),ly] for t in c.segments if c.board.GetLayerName(t.GetLayer())==ly and uid(t) not in retired]) for ly in faces};nets={p.GetNetname() for ref in refs for p in fps[ref].Pads()};foreign={(ly,n):unary_union([s for (u,l),s in c.shapes.items() if l==ly and u not in ids|retired|set(movable) and not isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=n]) for ly in faces for n in nets};poses={};rejections={} 
targets={'R1701':[('2','U1701.3')],'R1706':[('2','U1701.1')],'R1707':[('2','U1701.2')],'C1701':[('1','U1701.9'),('2','U1701.8')]};pads={c.pad_name(p):p for p in c.pads}
for ref in refs:
 old=fps[ref];origin=xy(old.GetPosition());oldangle=old.GetOrientationDegrees();owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')];assert len(owned)==1 and not any('_VIA_' in k['name'] for k in owned);reject=collections.Counter();rows=[]
 points=[(x/8,y/8) for x in range(328,432) for y in range(56,130)]+[origin]
 for face in (['B.Cu'] if ref=='C1701' else faces):
  for x,y in points:
   for angle in [0,90,180,270]:
    f=pcb.FOOTPRINT(old)
    if face=='F.Cu':f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));pp=[(p.GetNumber(),p.GetNetname(),shape(p,c.ids[face]),xy(p.GetPosition())) for p in f.Pads()];ds=[math.dist(next(p[3] for p in pp if p[0]==n),xy(pads[target].GetPosition())) for n,target in targets[ref]]
    if any(d>3+1e-9 for d in ds):reject['distance']+=1;continue
    body=fab(f);yard=outline(f,pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd)
    if body.intersection(fb[face]).area>1e-8 or yard.intersection(fy[face]).area>1e-8:reject['package_or_courtyard']+=1;continue
    if any(s.distance(vl[face])<.2-1e-6 for _,_,s,_ in pp):reject['fixed_vias']+=1;continue
    if any(s.distance(foreign[face,n])<.2-1e-6 for _,n,s,_ in pp):reject['foreign_copper']+=1;continue
    kk=[dict(k,shape=translate(rotate(scale(k['shape'],xfact=-1,yfact=1,origin=origin) if face=='F.Cu' else k['shape'],-(angle-(180-oldangle if face=='F.Cu' else oldangle)),origin=origin),xoff=x-origin[0],yoff=y-origin[1])) for k in owned]
    if any(k['vias'] and k['shape'].intersects(vl[face]) for k in kk):reject['fixed_via_native_guard']+=1;continue
    if any(k['tracks'] and k['shape'].intersects(ts[face]) for k in kk):reject['retained_track_native_guard']+=1;continue
    if body.difference(unary_union([p[2] for p in pp])).intersection(ts[face]).area>1e-8:reject['retained_track_under_body']+=1;continue
    conflicts=[u for u in movable if any(p[2].distance(c.shapes[u,face])<.2-1e-6 for p in pp) or any(k['vias'] and k['shape'].intersects(c.shapes[u,face]) for k in kk)]
    score=sum(ds)+.10*math.dist([x,y],origin)+.3*len(conflicts)+.5*(face=='F.Cu')
    row=dict(reference=ref,face=face,position_mm=[x,y],rotation_deg=angle,pads={p[0]:list(p[3]) for p in pp},target_distances_mm=ds,requires_via_relocation=conflicts,score=score);rows.append((row,body,yard,pp,kk))
 rows.sort(key=lambda a:a[0]['score']);poses[ref]=rows;rejections[ref]=dict(reject);print(ref,'poses',len(rows),flush=True)
# Beam of geometrically compatible partial layouts; result is bounded, not exhaustive.
beam=[([],0)]
for ref in sorted(refs,key=lambda r:len(poses[r])):
 expanded=[]
 for chosen,total in beam:
  for q in poses[ref]:
   if any(q[0]['face']==o[0]['face'] and (q[1].intersection(o[1]).area>1e-8 or q[2].intersection(o[2]).area>1e-8 or any(p[1]!=r[1] and p[2].distance(r[2])<.2-1e-6 for p in q[3] for r in o[3])) for o in chosen):continue
   expanded.append((chosen+[q],total+q[0]['score']))
 expanded.sort(key=lambda x:x[1]);beam=expanded[:500];print('beam',ref,len(expanded),len(beam),flush=True)
result=dict(scope=__doc__,comparison_sha256=c.sha,grid_mm=.125,beam_limit=500,prospectively_retired_tracks=sorted(retired),prospectively_movable_vias=[dict(uuid=u,net=v.GetNetname(),position_mm=list(xy(v.GetPosition()))) for u,v in movable.items()],rejections=rejections,poses={ref:[p[0] for p in rows] for ref,rows in poses.items()},joint_candidates=[dict(parts=[p[0] for p in ps],score=s) for ps,s in beam],adopted=False);out.write_text(json.dumps(result,indent=2)+'\n');print('joint',len(beam),flush=True)
for row in result['joint_candidates'][:3]:print(json.dumps(row),flush=True)
