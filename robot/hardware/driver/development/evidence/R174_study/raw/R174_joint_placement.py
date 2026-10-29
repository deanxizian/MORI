"""Read-only complete eight-part placement search using actual source thresholds.

Native courtyards, Fab bodies, pads, fixed via lands and exact owned rule areas
are used. All 114 GND vias stay fixed. Five explicitly named non-ground transfers
and 42 enumerated local source tracks are prospective replacements. Additional
retained-track clashes are dependencies, never waivers. No PCB is written.

All six existing critical adjacency constraints for these parts are loaded from
accepted R168G evidence. Extra CT/GND search bounds are recorded separately.
The finite grid/backtracking is not a global feasibility or routing proof.
"""
import ast,collections,functools,json,math,sys,time
from pathlib import Path
from shapely.affinity import rotate,translate,scale
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.strtree import STRtree
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *

b=Path('robot/.state/c3-completion/trials');out=b/'R174-joint-placement.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e';assert c.sha==expected
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
refs=['U1701','U1302','C1701','R1701','R1706','R1707','C1304','R1310'];fps={f.GetReference():f for f in c.footprints}
baseline=json.loads(Path('robot/hardware/driver/development/evidence/R168G/regression.json').read_text());checks=[x for x in baseline['critical_placement'] if all(x[k].split('.')[0] in refs for k in ['a','b'])];assert len(checks)==6
thresholds=[dict(a=x['a'],b=x['b'],target_max_mm=x['target_max_mm'],same_face_required=x['same_face_required'],source='R168G/regression.json') for x in checks]
search_bounds=[dict(a='U1302.4',b='R1310.1',target_max_mm=4,same_face_required=False,source='Additional CT placement search bound, not acceptance'),dict(a='U1302.2',b='C1304.2',target_max_mm=6,same_face_required=False,source='Additional bypass GND endpoint search bound, not acceptance')]
constraints=thresholds+search_bounds
base=json.loads((b/'R173-local-group-screen.json').read_text());assert base['source_sha256']==c.sha
retired=set(base['prospectively_retired_tracks']);movable=set(base['prospectively_movable_vias']);assert len(retired)==42 and len(movable)==5 and all(c.by_id[u].GetNetname()!='GND' for u in movable)
padids={uid(p) for p in c.pads if c.pad_name(p).split('.')[0] in refs};excluded=padids|retired|movable
vl={face:unary_union([c.shapes[uid(v),face] for v in c.vias if uid(v) not in movable]) for face in ['F.Cu','B.Cu']}
fixed={}
allnets={p.GetNetname() for ref in refs for p in fps[ref].Pads()}
for face in ['F.Cu','B.Cu']:
 lid=c.ids[face];yid=pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd
 rows=[(uid(t),t.GetNetname(),c.shapes[uid(t),face]) for t in c.segments if t.GetLayer()==lid and uid(t) not in retired]
 fixed[face]=dict(body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==lid and f.GetReference() not in refs]),yard=unary_union([outline(f,yid) for f in c.footprints if f.GetLayer()==lid and f.GetReference() not in refs]),foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly==face and u not in excluded and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=n]) for n in allnets},tracks=rows,tree=STRtree([r[2] for r in rows]))
templates={};poses={r:[] for r in refs};allposes=[];rejects={r:collections.Counter() for r in refs};started=time.monotonic()
for ref in refs:
 old=fps[ref];origin=xy(old.GetPosition());original_face=c.board.GetLayerName(old.GetLayer());owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
 bg=unary_union([k['shape'] for k in owned if k['tracks']]);vg=unary_union([k['shape'] for k in owned if k['vias']]);holes=bg.difference(vg);assert vg.difference(bg).area<1e-8
 faces=['B.Cu','F.Cu'] if ref.startswith('R') else [original_face]
 for face in faces:
  template=pcb.FOOTPRINT(old);guard=bg;angle0=old.GetOrientationDegrees();cuts=holes
  if face!=original_face:
   assert ref.startswith('R') and not any('_VIA_' in k['name'] for k in owned)
   template.Flip(template.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);angle0=template.GetOrientationDegrees();guard=scale(bg,xfact=-1,yfact=1,origin=origin);cuts=GeometryCollection()
  for angle in [0,90,180,270]:
   ff=pcb.FOOTPRINT(template);ff.SetOrientationDegrees(angle);lid=c.ids[face];yardid=pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd
   templates[ref,face,angle]=dict(origin=origin,face=face,body=fab(ff),yard=outline(ff,yardid),pads={p.GetNumber():dict(net=p.GetNetname(),shape=shape(p,lid),position_mm=xy(p.GetPosition())) for p in ff.Pads()},guard=rotate(guard,-(angle-angle0),origin=origin),fixed_cutouts=cuts)

def make_pose(ref,face,angle,x,y):
 t=templates[ref,face,angle];dx=x-t['origin'][0];dy=y-t['origin'][1];tr=lambda s:translate(s,xoff=dx,yoff=dy)
 body=tr(t['body']);yard=tr(t['yard']);env=fixed[face];reject=rejects[ref]
 if body.intersection(env['body']).area>1e-8 or yard.intersection(env['yard']).area>1e-8:reject['fixed_body_courtyard']+=1;return
 pp={n:dict(net=p['net'],shape=tr(p['shape']),position_mm=[round(p['position_mm'][0]+dx,6),round(p['position_mm'][1]+dy,6)]) for n,p in t['pads'].items()}
 if any(p['shape'].distance(vl[face])<.1999996-1e-9 for p in pp.values()):reject['fixed_via_pad']+=1;return
 if any(p['shape'].distance(env['foreign'][p['net']])<.1999996-1e-9 for p in pp.values()):reject['fixed_pad']+=1;return
 guard=tr(t['guard']);via_guard=guard.difference(t['fixed_cutouts'])
 if via_guard.intersection(vl[face]).area>1e-8:reject['native_fixed_via_guard']+=1;return
 pads_union=unary_union([p['shape'] for p in pp.values()]);outside=body.difference(pads_union);query=unary_union([outside,guard,pads_union.buffer(.2)])
 deps=[]
 for i in env['tree'].query(query):
  u,net,s=env['tracks'][int(i)]
  if outside.intersection(s).area>1e-8 or guard.intersection(s).area>1e-8 or any(net!=p['net'] and s.distance(p['shape'])<.1999996-1e-9 for p in pp.values()):deps.append(u)
 if len(deps)>6:reject['more_than_six_track_dependencies']+=1;return
 row=dict(id=len(allposes),reference=ref,face=face,position_mm=[x,y],rotation_deg=angle,pads=pp,body=body,yard=yard,guard=guard,via_guard=via_guard,dependencies=frozenset(deps),score=.1*math.dist([x,y],t['origin'])+1.5*(face!=c.board.GetLayerName(fps[ref].GetLayer()))+.15*(angle!=fps[ref].GetOrientationDegrees()))
 allposes.append(row);poses[ref].append(row['id']);return row

# Initial four geometrically distinct R172 short-listed IC poses. Other parts
# have a 0.25 mm local grid plus their exact source pose where not on that grid.
ina_seeds=[(46.75,14,0),(48.75,12.25,90),(46.25,14,180),(44.25,12.25,270)]
for x,y,a in ina_seeds:make_pose('U1701','B.Cu',a,x,y)
for ref in refs[1:]:
 for face in (['B.Cu','F.Cu'] if ref.startswith('R') else ['B.Cu']):
  for angle in [0,90,180,270]:
   for x in [i/4 for i in range(164,217)]:
    for y in [i/4 for i in range(24,81)]:make_pose(ref,face,angle,x,y)
  original=fps[ref]
  if face==c.board.GetLayerName(original.GetLayer()):make_pose(ref,face,int(original.GetOrientationDegrees())%360,*xy(original.GetPosition()))
 print(json.dumps(dict(stage='pose_generation',reference=ref,poses=len(poses[ref]),elapsed_seconds=round(time.monotonic()-started,3))),flush=True)

by_pair=collections.defaultdict(list)
for k in constraints:
 ar,ap=k['a'].split('.');br,bp=k['b'].split('.');by_pair[ar,br].append((ap,bp,k));by_pair[br,ar].append((bp,ap,k))
@functools.lru_cache(maxsize=1500000)
def compatible_ids(ai,bi):
 a,z=allposes[ai],allposes[bi]
 for ap,bp,k in by_pair[a['reference'],z['reference']]:
  if math.dist(a['pads'][ap]['position_mm'],z['pads'][bp]['position_mm'])>k['target_max_mm']+1e-6 or (k['same_face_required'] and a['face']!=z['face']):return False
 if a['face']!=z['face']:return True
 if a['yard'].intersection(z['yard']).area>1e-8 or a['body'].intersection(z['body']).area>1e-8:return False
 return all(p['net']==q['net'] or p['shape'].distance(q['shape'])>=.1999996-1e-9 for p in a['pads'].values() for q in z['pads'].values())

def serial(row):
 return dict(reference=row['reference'],face=row['face'],position_mm=row['position_mm'],rotation_deg=row['rotation_deg'],pads={n:dict(net=p['net'],position_mm=p['position_mm']) for n,p in row['pads'].items()},retained_track_dependencies=sorted(row['dependencies']))
def final_score(chosen):
 rows=[allposes[i] for i in chosen.values()];dep=set().union(*(r['dependencies'] for r in rows));score=8*len(dep)+sum(r['score'] for r in rows)
 for k in constraints:
  ar,ap=k['a'].split('.');br,bp=k['b'].split('.');score+=math.dist(allposes[chosen[ar]]['pads'][ap]['position_mm'],allposes[chosen[br]]['pads'][bp]['position_mm'])
 # Prefer a short, same-face explicit RLIMIT return. This is a preference,
 # never a substitute for an actually routed/verified direct return path.
 aa=allposes[chosen['U1701']];rr=allposes[chosen['R1701']];score+=math.dist(aa['pads']['8']['position_mm'],rr['pads']['1']['position_mm'])+2*(aa['face']!=rr['face'])
 return score,dep

results=[];audits=[]
for ui in poses['U1701']:
 u=allposes[ui];initial={r:[j for j in poses[r] if compatible_ids(ui,j)] for r in refs if r!='U1701'}
 counts={r:len(v) for r,v in initial.items()};local=[];nodes=0;pruned=collections.Counter();start=time.monotonic();node_limit=25000;seconds_limit=75;solution_limit=40
 def search(chosen,domains,deps):
  nonlocal_placeholder=None
  global nodes
  if nodes>=node_limit or time.monotonic()-start>=seconds_limit or len(local)>=solution_limit:return
  nodes+=1
  if not domains:
   score,dd=final_score(chosen);local.append(dict(score=score,parts=[serial(allposes[chosen[r]]) for r in refs],additional_track_dependencies=sorted(dd)));return
  r=min(domains,key=lambda ref:(len(domains[ref]),0 if ref in ['U1302','C1701'] else 1))
  order=sorted(domains[r],key=lambda j:8*len(allposes[j]['dependencies']-deps)+allposes[j]['score'])
  for j in order:
   if nodes>=node_limit or time.monotonic()-start>=seconds_limit or len(local)>=solution_limit:break
   newdeps=deps|allposes[j]['dependencies']
   if len(newdeps)>12:pruned['more_than_12_track_dependencies']+=1;continue
   nd={};bad=False
   for s,ids in domains.items():
    if s==r:continue
    compatible=[k for k in ids if compatible_ids(j,k)]
    if not compatible:pruned['empty_'+s]+=1;bad=True;break
    nd[s]=compatible
   if not bad:search(dict(chosen,**{r:j}),nd,newdeps)
 if all(initial.values()):search({'U1701':ui},initial,u['dependencies'])
 else:pruned['initial_empty_domain']+=1
 local.sort(key=lambda r:r['score']);results.extend(local)
 audit=dict(INA300=serial(u),initial_domains=counts,nodes=nodes,elapsed_seconds=time.monotonic()-start,solutions=len(local),pruned=dict(pruned),node_limit=node_limit,seconds_limit=seconds_limit,solution_limit=solution_limit,bounded_stop=nodes>=node_limit or time.monotonic()-start>=seconds_limit or len(local)>=solution_limit);audits.append(audit)
 print(json.dumps({k:v for k,v in audit.items() if k!='INA300'}|dict(INA_position=u['position_mm'],INA_rotation=u['rotation_deg'])),flush=True)
results.sort(key=lambda r:r['score'])
result=dict(scope=__doc__,source_sha256=c.sha,loaded_critical_thresholds=thresholds,additional_search_bounds=search_bounds,grid_mm=.25,passive_bounds_mm=[41,6,54,20],prospectively_moved_parts=refs,prospectively_retired_tracks=sorted(retired),prospectively_movable_non_ground_vias=sorted(movable),source_GND_vias_fixed=114,pose_counts={r:len(v) for r,v in poses.items()},rejections={r:dict(v) for r,v in rejects.items()},searches=audits,full_eight_part_solutions=len(results),solutions=results[:80],elapsed_seconds=time.monotonic()-started,adopted=False,native_DRC='NOT_TESTED')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(full_solutions=len(results),best=results[0] if results else None,elapsed_seconds=result['elapsed_seconds'])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
