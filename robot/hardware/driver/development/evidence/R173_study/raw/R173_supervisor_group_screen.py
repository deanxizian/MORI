"""Read-only U1302/R1310/C1304 grouped relocation comparison from R168G.

Only those three parts, their enumerated source pad leads, the CT network leads
and its single non-ground via are prospectively replaced. All other geometry,
all source GND vias and exact native body guards stay hard constraints. Reserve
the two shortlisted INA300 courtyards for later joint placement. This is not
routing, an electrical acceptance result, or proof of global feasibility.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R173-supervisor-group-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
refs={'U1302','R1310','C1304'};fps={f.GetReference():f for f in c.footprints}
padids={uid(p) for ref in refs for p in fps[ref].Pads()};ct='Net-(U1302-CT)'
oldvia=[v for v in c.vias if v.GetNetname()==ct];assert len(oldvia)==1;viaids={uid(v) for v in oldvia}
retired={uid(t) for t in c.segments if t.GetNetname()==ct}
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer());s=c.shapes[uid(t),ly]
 if any(t.GetNetname()==c.by_id[u].GetNetname() and (u,ly) in c.shapes and s.intersects(c.shapes[u,ly]) for u in padids):retired.add(uid(t))
exclude=padids|retired|viaids
body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in refs])
yards=unary_union([outline(f,pcb.B_CrtYd) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in refs])
reserve=[]
for x,y,a in [(46.75,14,0),(48.75,12.25,90)]:
 f=pcb.FOOTPRINT(fps['U1701']);f.SetOrientationDegrees(a);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));reserve.append(outline(f,pcb.B_CrtYd))
yards=unary_union([yards]+reserve)
vl=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias if uid(v) not in viaids])
ts=unary_union([c.shapes[uid(t),'B.Cu'] for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in retired])
nets={p.GetNetname() for ref in refs for p in fps[ref].Pads()}
foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in exclude and not isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=n]) for n in nets}
templates={};guarddata={}
for ref in refs:
 f=pcb.FOOTPRINT(fps[ref]);owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
 origin=xy(f.GetPosition());angle=f.GetOrientationDegrees()
 bg=unary_union([k['shape'] for k in owned if k['tracks']]);vg=unary_union([k['shape'] for k in owned if k['vias']]);holes=bg.difference(vg)
 if ref=='R1310':
  f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);angle=f.GetOrientationDegrees()
  # R1310 has a symmetric simple rectangular guard, verified here.
  from shapely.affinity import scale
  bg=scale(bg,xfact=-1,yfact=1,origin=origin);holes=GeometryCollection()
 templates[ref]=f;guarddata[ref]=(origin,angle,bg,holes)

def pose(ref,x,y,angle,reject):
 f=pcb.FOOTPRINT(templates[ref]);f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)))
 bd=fab(f);yd=outline(f,pcb.B_CrtYd)
 if bd.intersection(body).area>1e-8 or yd.intersection(yards).area>1e-8:reject['body_or_courtyard']+=1;return
 pp={p.GetNumber():dict(net=p.GetNetname(),position_mm=list(xy(p.GetPosition())),shape=shape(p,pcb.B_Cu)) for p in f.Pads()}
 if any(p['shape'].distance(vl)<.2-1e-6 for p in pp.values()):reject['fixed_via_pad']+=1;return
 if any(p['shape'].distance(foreign[p['net']])<.2-1e-6 for p in pp.values()):reject['retained_copper']+=1;return
 origin,oldangle,bg,holes=guarddata[ref];tg=translate(rotate(bg,-(angle-oldangle),origin=origin),xoff=x-origin[0],yoff=y-origin[1]);vg=tg.difference(holes)
 if vg.intersection(vl).area>1e-8:reject['native_fixed_via_guard']+=1;return
 if tg.intersection(ts).area>1e-8:reject['native_retained_track_guard']+=1;return
 if bd.difference(unary_union([p['shape'] for p in pp.values()])).intersection(ts).area>1e-8:reject['retained_track_under_body']+=1;return
 return dict(reference=ref,position_mm=[x,y],rotation_deg=angle,pads=pp,body=bd,yard=yd)

def compatible(a,b):
 return a['yard'].intersection(b['yard']).area<1e-8 and all(pa['net']==pb['net'] or pa['shape'].distance(pb['shape'])>=.2-1e-6 for pa in a['pads'].values() for pb in b['pads'].values())

def serial(row):
 return {k:({n:{kk:vv for kk,vv in v.items() if kk!='shape'} for n,v in val.items()} if k=='pads' else val) for k,val in row.items() if k not in ['body','yard']}

start=time.monotonic();reject={r:collections.Counter() for r in refs};poses={r:[] for r in refs}
# Broad rear region, all positions remain within fixed board outline.
for ref in ['U1302','C1304','R1310']:
 for x in [v/4 for v in range(112,213)]:
  for y in [v/4 for v in range(56,131)]:
   for a in [0,90,180,270]:
    row=pose(ref,x,y,a,reject[ref])
    if row:poses[ref].append(row)
 print(json.dumps(dict(reference=ref,poses=len(poses[ref]),rejections=dict(reject[ref]),elapsed_seconds=time.monotonic()-start)),flush=True)
groups=[]
for u in poses['U1302']:
 up=u['pads'];caps=[v for v in poses['C1304'] if math.dist(up['5']['position_mm'],v['pads']['1']['position_mm'])<=3.0 and math.dist(up['2']['position_mm'],v['pads']['2']['position_mm'])<=3.0 and compatible(u,v)]
 resistors=[v for v in poses['R1310'] if math.dist(up['4']['position_mm'],v['pads']['1']['position_mm'])<=3.0 and compatible(u,v)]
 caps.sort(key=lambda v:math.dist(up['5']['position_mm'],v['pads']['1']['position_mm'])+math.dist(up['2']['position_mm'],v['pads']['2']['position_mm']))
 resistors.sort(key=lambda v:math.dist(up['4']['position_mm'],v['pads']['1']['position_mm'])+math.dist(up['5']['position_mm'],v['pads']['2']['position_mm']))
 local=[]
 for cap in caps[:20]:
  for r in resistors[:20]:
   if not compatible(cap,r):continue
   score=math.dist(u['position_mm'],[49,15.85])+.7*(math.dist(up['5']['position_mm'],cap['pads']['1']['position_mm'])+math.dist(up['2']['position_mm'],cap['pads']['2']['position_mm'])+math.dist(up['4']['position_mm'],r['pads']['1']['position_mm']))
   local.append(dict(score=score,parts=[serial(u),serial(cap),serial(r)]))
 if local:groups.extend(sorted(local,key=lambda v:v['score'])[:2])
groups.sort(key=lambda v:v['score'])
result=dict(scope=__doc__,source_sha256=c.sha,prospectively_moved_parts=sorted(refs),prospectively_retired_tracks=sorted(retired),prospectively_obsolete_CT_via=uid(oldvia[0]),grid_mm=.25,bounds_mm=[28,14,53,32.5],reserved_INA300_courtyards=[dict(position_mm=[46.75,14],rotation_deg=0),dict(position_mm=[48.75,12.25],rotation_deg=90)],pose_counts={r:len(v) for r,v in poses.items()},rejections={r:dict(v) for r,v in reject.items()},group_count=len(groups),best_groups=groups[:80],elapsed_seconds=time.monotonic()-start,native_DRC='NOT_TESTED',adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['scope','best_groups','rejections']}),flush=True)
for g in groups[:8]:print(json.dumps(dict(score=g['score'],parts=[{k:v for k,v in p.items() if k!='pads'} for p in g['parts']])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
