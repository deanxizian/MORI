"""Bounded cost-guided full eight-part CSP, retaining source acceptance rules.

Uses R174 native pose generation. Connection length, opposite-face transitions,
extra retained tracks and actually intersected prospective transfer sites affect
ranking only. No guessed routing feasibility or new acceptance threshold.
"""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_joint_placement.py').read_text()
src=src.split('results=[];audits=[]')[0]
src=src.replace("out=b/'R174-joint-placement.json'", "out=b/'R174-ranked-placement.json'")
exec(compile(src,'R174_joint_placement.py','exec'))
ranking_pairs=constraints+[dict(a='R1701.1',b='U1701.8',weight=2),dict(a='C1701.2',b='U1701.8',weight=1)]
rank_by_pair=collections.defaultdict(list)
for k in ranking_pairs:
 ar,ap=k['a'].split('.');br,bp=k['b'].split('.')
 rank_by_pair[ar,br].append((ap,bp,k.get('weight',1)))
 rank_by_pair[br,ar].append((bp,ap,k.get('weight',1)))
for row in allposes:
 deps=[]
 for vi in movable:
  land=c.shapes[vi,row['face']]
  if any(p['shape'].distance(land)<.1999996-1e-9 for p in row['pads'].values()) or row['via_guard'].intersection(land).area>1e-8:
   deps.append(vi)
 row['via_dependencies']=frozenset(deps)

@functools.lru_cache(maxsize=1500000)
def pair_cost(ai,bi):
 a,z=allposes[ai],allposes[bi]
 return sum(w*math.dist(a['pads'][ap]['position_mm'],z['pads'][bp]['position_mm'])+3*(a['face']!=z['face']) for ap,bp,w in rank_by_pair[a['reference'],z['reference']])

def increment(j,chosen,deps,via_deps):
 r=allposes[j]
 return r['score']+8*len(r['dependencies']-deps)+4*len(r['via_dependencies']-via_deps)+sum(pair_cost(j,k) for k in chosen.values())

results=[];audits=[]
for ui in poses['U1701']:
 u=allposes[ui];initial={r:[j for j in poses[r] if compatible_ids(ui,j)] for r in refs if r!='U1701'}
 nodes=0;pruned=collections.Counter();start=time.monotonic();limit=60;node_limit=30000;local=[];best=float('inf')
 def search(chosen,domains,deps,via_deps,cost):
  global nodes,best
  if nodes>=node_limit or time.monotonic()-start>=limit:return
  nodes+=1
  if not domains:
   row=dict(score=cost,parts=[serial(allposes[chosen[r]]) for r in refs],additional_track_dependencies=sorted(deps),actually_intersected_transfer_sites=sorted(via_deps))
   local.append(row);local.sort(key=lambda x:x['score']);del local[20:]
   if cost<best:
    best=cost;print(json.dumps(dict(stage='improved_complete_placement',INA_position=u['position_mm'],INA_rotation=u['rotation_deg'],score=best,nodes=nodes,elapsed_seconds=time.monotonic()-start)),flush=True)
   return
  # A valid optimistic bound: do not charge future shared dependencies twice.
  lower=cost+sum(min(allposes[j]['score']+sum(pair_cost(j,k) for k in chosen.values()) for j in ids) for ids in domains.values())
  if len(local)>=20 and lower>=local[-1]['score']-1e-8:pruned['cost_bound']+=1;return
  r=min(domains,key=lambda rr:(len(domains[rr]),0 if rr in ['U1302','C1701'] else 1))
  order=sorted(domains[r],key=lambda j:increment(j,chosen,deps,via_deps))
  for j in order:
   if nodes>=node_limit or time.monotonic()-start>=limit:break
   newdeps=deps|allposes[j]['dependencies'];newvia=via_deps|allposes[j]['via_dependencies'];inc=increment(j,chosen,deps,via_deps)
   if len(newdeps)>12:pruned['track_dependency_bound']+=1;continue
   if len(local)>=20 and cost+inc>local[-1]['score']:continue
   nd={};bad=False
   for s,ids in domains.items():
    if s==r:continue
    ok=[k for k in ids if compatible_ids(j,k)]
    if not ok:pruned['empty_'+s]+=1;bad=True;break
    nd[s]=ok
   if not bad:search(dict(chosen,**{r:j}),nd,newdeps,newvia,cost+inc)
 if all(initial.values()):search({'U1701':ui},initial,u['dependencies'],u['via_dependencies'],increment(ui,{},set(),set()))
 local.sort(key=lambda x:x['score']);results.extend(local)
 audits.append(dict(INA=serial(u),nodes=nodes,elapsed_seconds=time.monotonic()-start,seconds_limit=limit,node_limit=node_limit,bounded_stop=nodes>=node_limit or time.monotonic()-start>=limit,best_score=best if local else None,kept_solutions=len(local),pruned=dict(pruned)))
 print(json.dumps(dict(stage='seed_complete',**{k:v for k,v in audits[-1].items() if k!='INA'})),flush=True)
results.sort(key=lambda x:x['score'])
result=dict(scope=__doc__,source_sha256=c.sha,thresholds=thresholds,additional_search_bounds=search_bounds,prospectively_retired_tracks=sorted(retired),prospectively_movable_vias=sorted(movable),fixed_source_GND_vias=114,searches=audits,solutions=results,adopted=False,native_DRC='NOT_TESTED')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(stage='done',solutions=len(results),best=results[0] if results else None)),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
