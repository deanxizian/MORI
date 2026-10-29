"""Broader complete-group screen with native outward-escape ranking.

Expands INA300 poses beyond the four initial seeds, including the exact adopted
pose. Pin escape lengths only rank candidates; they are not new acceptance
thresholds. Critical adjacency and fixed native geometry remain unchanged.
No PCB is written and the finite search cannot establish whole-board no-fit.
"""
from pathlib import Path
base=Path('robot/.state/c3-completion/trials/R174_ranked_placement.py').read_text()
base=base.replace("src=src.replace(\"out=b/'R174-joint-placement.json'\", \"out=b/'R174-ranked-placement.json'\")", "src=src.replace(\"out=b/'R174-joint-placement.json'\", \"out=b/'R174-expanded-placement.json'\")\nsrc=src.replace('ina_seeds=[(46.75,14,0),(48.75,12.25,90),(46.25,14,180),(44.25,12.25,270)]', 'ina_seeds=[(x/4,y/4,a) for a in [0,90,180,270] for x in range(164,217) for y in range(24,81)]+[(47.25,12.35,0)]')")
base=base.replace('results=[];audits=[]', '''
escape_rows=[]
for i in poses['U1701']:
 row=allposes[i];ends={};face=row['face'];center=row['position_mm']
 for pn in ['1','2','3','4','5','8','9']:
  pp=row['pads'][pn];x,y=pp['position_mm'];dx=x-center[0];dy=y-center[1]
  direction=(1 if dx>0 else -1,0) if abs(dx)>abs(dy) else (0,1 if dy>0 else -1)
  distance=(pp['shape'].bounds[2]-pp['shape'].bounds[0])/2 if direction[0] else (pp['shape'].bounds[3]-pp['shape'].bounds[1])/2
  foreign=[fixed[face]['foreign'][pp['net']]]
  foreign += [c.shapes[uid(v),face] for v in c.vias if uid(v) not in movable and v.GetNetname()!=pp['net']]
  foreign += [r['shape'] for n,r in row['pads'].items() if r['net']!=pp['net']]
  foreign += [s for u,n,s in fixed[face]['tracks'] if u not in row['dependencies'] and n!=pp['net']]
  obstacles=unary_union(foreign)
  best_escape=0
  for length in [.15,.3,.5,.75]:
   end=[x+direction[0]*(distance+length),y+direction[1]*(distance+length)]
   if LineString([(x,y),end]).buffer(.1).distance(obstacles)>=.1999996-1e-9:best_escape=length
   else:break
  ends[pn]=best_escape
 score=12*sum(v<.3 for v in ends.values())+4*len(row['dependencies'])+sum(.75-v for v in ends.values())+row['score']
 escape_rows.append(dict(id=i,position_mm=row['position_mm'],rotation_deg=row['rotation_deg'],outward_escape_mm=ends,ranking_score=score))
escape_rows.sort(key=lambda x:x['ranking_score'])
selected=[]
for angle in [0,90,180,270]:selected += [r['id'] for r in escape_rows if r['rotation_deg']==angle][:8]
original=next(r for r in escape_rows if r['position_mm']==[47.25,12.35] and r['rotation_deg']==0)
if original['id'] not in selected:selected.append(original['id'])
all_ina_count=len(poses['U1701']);poses['U1701']=selected
print(json.dumps(dict(stage='expanded_INA_escape_ranking',eligible_poses=all_ina_count,selected=len(selected),best=escape_rows[:6])),flush=True)
results=[];audits=[]
''')
base=base.replace('limit=60;node_limit=30000','limit=6;node_limit=6000')
base=base.replace('del local[20:]','del local[4:]').replace('len(local)>=20','len(local)>=4')
base=base.replace("fixed_source_GND_vias=114,searches=audits", "fixed_source_GND_vias=114,all_INA_pose_count=all_ina_count,outward_escape_ranking=escape_rows,selected_INA_poses=selected,searches=audits")
exec(compile(base,'R174_expanded_placement.py','exec'))
