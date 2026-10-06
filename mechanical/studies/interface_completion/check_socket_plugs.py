"""Recheck all29 earlier manufacturer plug envelopes with candidate sockets."""
import sys,json,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,broad,rigidtr
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
old=HERE.parent/'prearrival_preparation';previous=json.loads((old/'mated_connector_review.json').read_text())
with bpy.data.libraries.load(str(old/'mated_connector_review.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(PREFIX+'PREARRIVAL_Plug_')]
for o in dst.objects:
 if o:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon'] and o.name!=PREFIX+'MCU_Motion'}
for o in bpy.data.objects:
 if o.name.startswith(PREFIX+'STUDY_'):solids[o.name.removeprefix(PREFIX)]=Solid(o)
plugs={o.name.removeprefix(PREFIX):Solid(o) for o in dst.objects if o};rows=[]
def volume(a,b):
 bb=np.array(a.bounding_box())
 return max(0,(a^b.m).volume()) if np.all(bb[3:]>=b.lo) and np.all(b.hi>=bb[:3]) else 0
for r in previous['rows']:
 name='PREARRIVAL_Plug_'+r['board']+'_'+r['ref'];s=plugs[name];hits=[];path=[];owner=P['native_electronics']['boards'][r['board']]['object']
 for n,t in solids.items():
  if n==owner or n==name:continue
  v=volume(s.m,t)
  if v>.01:hits.append({'target':n,'overlap_mm3':v})
 # Retain only same-native-PCB component intersections from the original study;
 # those source meshes are unchanged. Mating header itself is excluded explicitly.
 hits.extend(h for h in r['overlap_candidates'] if h['target'].startswith(owner+'/'))
 for d in range(1,13):
  sm=s.m.translate((np.array(r['axis'])*d).tolist())
  for n,t in solids.items():
   if n==owner or n==name:continue
   v=volume(sm,t)
   if v>.01:path.append({'travel_mm':d,'target':n,'overlap_mm3':v})
 rows.append({**r,'static_status':'FAIL' if hits else 'PASS','overlap_candidates':hits,'insertion_status':'BLOCKED' if path else 'PASS','straight_path_12mm_candidates':path})
pairs=[]
for (n,a),(k,b) in itertools.combinations(plugs.items(),2):
 v=volume(a.m,b)
 if v>.01:pairs.append({'a':n,'b':k,'overlap_mm3':v})
moving=[]
for yaw in range(-60,61,10):
 for pitch in range(-20,26,5):
  for n,s in solids.items():
   if s.group not in ['yaw','pitch']:continue
   t=Solid(s.o,s,rigidtr(yaw,pitch if s.group=='pitch' else 0))
   for k,a in plugs.items():
    v=volume(a.m,t)
    if v>.01:moving.append({'yaw':yaw,'pitch':pitch,'plug':k,'moving':n,'overlap_mm3':v})
 print('MATED_POSE_YAW',yaw,flush=True)
out={'revision':P['revision']+' + unadopted raised-core candidate','main_updated':False,'rows':rows,'plug_pair_hits':pairs,'poses':130,'motion_collisions':moving,'source_report':str((old/'mated_connector_review.json').relative_to(PROJECT)),'socket_candidate':'socket_candidate.json','limits':'Rigid documented PH/XH outer envelopes; XT30 deliberately conservative full unengaged length. A blocked straight path needs explicit assembly staging. No cable bend/hand/latch/continuity qualification.'}
(HERE/'socket_plug_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('SOCKET_PLUGS',len(rows),[(r['board'],r['ref'],r['overlap_candidates']) for r in rows if r['overlap_candidates']],len(pairs),len(moving),flush=True)
