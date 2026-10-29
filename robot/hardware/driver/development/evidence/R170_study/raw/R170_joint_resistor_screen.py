"""Read-only joint R1701/R1707 placement candidates, not routed acceptance.

Explicitly retire their old terminal leads for this screen. All GND vias and
all other parts remain fixed. A prospective WHEEL tap-via conflict is recorded,
not waived: a real plan must either keep it clear or relocate it explicitly.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import translate,rotate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170-joint-resistor-screen.json';assert not out.exists();c=Copper(b/'R170B/MORI_Interface_C3.kicad_pcb');fps={f.GetReference():f for f in c.footprints};refs=['R1701','R1707'];padids={uid(p) for ref in refs for p in fps[ref].Pads()};retired={'4da58487-f076-5185-8828-943f5727193f','9e2909c0-b0c9-5aa7-9c9e-244071604eab','b57bf843-5b94-5584-a10e-602aeff0f3e3','0de6273a-710d-5be6-9fbf-0d57ba814746','16f0053d-a9c2-5596-9d50-1dae60235368','5be216ee-2f22-542d-b56c-b0fba2ef0a7b','ad8bf9ab-c57f-55b6-993f-db8012d24229','bc1cff30-589b-5342-b4eb-e07415cd3de1','c040599d-733a-5160-b4bf-a7e26a34ad04','fa9d0cc6-e3a3-5fe4-953f-d311beca4b4a'}
wheel=next(v for v in c.vias if xy(v.GetPosition())==(42.55,14.2));assert wheel.GetNetname()=='/WHEEL_VM';wid=uid(wheel)
tree=ast.parse((b/'R167_joint_pose_screen.py').read_text())
for name in ['fab','outline']:
 t=ast.parse((b/'R138_joint_search.py').read_text()) if name=='fab' else tree;n=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),name,'exec'))
faces=['B.Cu','F.Cu'];fb={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference() not in refs]) for ly in faces};fy={ly:unary_union([outline(f,pcb.F_CrtYd if ly=='F.Cu' else pcb.B_CrtYd) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference() not in refs]) for ly in faces};vl={ly:unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PCB_VIA) and u!=wid]) for ly in faces};ts={ly:unary_union([c.shapes[uid(t),ly] for t in c.segments if c.board.GetLayerName(t.GetLayer())==ly and uid(t) not in retired]) for ly in faces};nets={p.GetNetname() for ref in refs for p in fps[ref].Pads()};foreign={(ly,n):unary_union([s for (u,l),s in c.shapes.items() if l==ly and u not in padids|retired and not isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=n]) for ly in faces for n in nets};poses={};controls={};rejections={}
for ref,target in [('R1701','U1701.3'),('R1707','U1701.2')]:
 old=fps[ref];origin=xy(old.GetPosition());oldangle=old.GetOrientationDegrees();owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')];assert len(owned)==1 and not any('_VIA_' in k['name'] for k in owned);targetpad=next(p for p in c.pads if c.pad_name(p)==target);reject=collections.Counter();rows=[];controls[ref]=False
 points=[(x/8,y/8) for x in range(332,389) for y in range(74,125)]+[origin]
 for face in faces:
  for x,y in points:
   for angle in [0,90,180,270]:
    f=pcb.FOOTPRINT(old)
    if face=='F.Cu':f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));pp=[(p.GetNumber(),p.GetNetname(),shape(p,c.ids[face]),xy(p.GetPosition())) for p in f.Pads()];ip=next(p[3] for p in pp if p[0]=='2');op=next(p[3] for p in pp if p[0]=='1');dist=math.dist(ip,xy(targetpad.GetPosition()))
    if dist>3+1e-9:reject['distance']+=1;continue
    body=fab(f);yard=outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd)
    if body.intersection(fb[face]).area>1e-8 or yard.intersection(fy[face]).area>1e-8:reject['package_or_courtyard']+=1;continue
    if any(s.distance(vl[face])<.2-1e-6 for _,_,s,_ in pp):reject['fixed_vias']+=1;continue
    if any(s.distance(foreign[face,n])<.2-1e-6 for _,n,s,_ in pp):reject['foreign_copper']+=1;continue
    kk=[]
    for k in owned:
     before=scale(k['shape'],xfact=-1,yfact=1,origin=origin) if face=='F.Cu' else k['shape'];a=angle-(180-oldangle) if face=='F.Cu' else angle-oldangle;kk.append(dict(k,shape=translate(rotate(before,-a,origin=origin),xoff=x-origin[0],yoff=y-origin[1])))
    if any(k['vias'] and k['shape'].intersects(vl[face]) for k in kk):reject['fixed_via_native_guard']+=1;continue
    if any(k['tracks'] and k['shape'].intersects(ts[face]) for k in kk):reject['retained_track_native_guard']+=1;continue
    if body.difference(unary_union([p[2] for p in pp])).intersection(ts[face]).area>1e-8:reject['retained_track_under_body']+=1;continue
    conflict=any(p[2].distance(c.shapes[wid,face])<.2-1e-6 for p in pp) or any(k['vias'] and k['shape'].intersects(c.shapes[wid,face]) for k in kk)
    if face=='B.Cu' and [x,y]==list(origin) and angle==oldangle:controls[ref]=True
    row=dict(reference=ref,face=face,position_mm=[x,y],rotation_deg=angle,input_pad_mm=list(ip),other_pad_mm=list(op),input_distance_mm=dist,requires_WHEEL_via_relocation=conflict,displacement_mm=math.dist([x,y],origin));rows.append((row,body,yard,pp,kk))
 poses[ref]=rows;rejections[ref]=dict(reject);print(ref,'poses',len(rows),'unchanged control',controls[ref],flush=True)
pairs=[]
for a in poses['R1701']:
 if not(a[0]['input_pad_mm'][0]<44.1 and a[0]['input_pad_mm'][1]>10.6):continue
 for z in poses['R1707']:
  if a[0]['face']==z[0]['face']:
   if a[1].intersection(z[1]).area>1e-8 or a[2].intersection(z[2]).area>1e-8:continue
   if any(p[1]!=q[1] and p[2].distance(q[2])<.2-1e-6 for p in a[3] for q in z[3]):continue
  score=a[0]['input_distance_mm']+z[0]['input_distance_mm']+.15*(a[0]['displacement_mm']+z[0]['displacement_mm'])+2*(a[0]['requires_WHEEL_via_relocation'] or z[0]['requires_WHEEL_via_relocation'])+.5*(a[0]['face']=='F.Cu')+.5*(z[0]['face']=='F.Cu');pairs.append(dict(R1701=a[0],R1707=z[0],score=score))
pairs.sort(key=lambda r:r['score']);result=dict(scope=__doc__,comparison_sha256=c.sha,prospectively_retired_tracks=sorted(retired),prospectively_movable_WHEEL_via=wid,unchanged_pose_controls=controls,rejections=rejections,poses={k:[p[0] for p in v] for k,v in poses.items()},joint_candidates=pairs,adopted=False);out.write_text(json.dumps(result,indent=2)+'\n');print('joint',len(pairs),flush=True)
for row in pairs[:8]:print(json.dumps(row),flush=True)
assert all(controls.values())
