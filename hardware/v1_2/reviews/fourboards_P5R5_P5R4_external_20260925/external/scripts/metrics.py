from analyze import *
import networkx as nx
from shapely.geometry import Point,LineString
from run_geometry import padshape
OUT=Path('/mnt/data/latest_review_work/evidence')

def pad(d,ref,num):return next(p for p in d['footprints'][ref]['pads'] if p['num']==str(num))

def path_metrics(d,ref1,num1,ref2,num2):
 p1,p2=pad(d,ref1,num1),pad(d,ref2,num2)
 if p1['net']!=p2['net']:return {'error':'different_nets','net1':p1['net'],'net2':p2['net']}
 net=p1['net'];seg=[s for s in d['segments'] if s['net']==net];vias=[v for v in d['vias'] if v['net']==net]
 G=nx.Graph();coords=collections.defaultdict(set)
 for s in seg:
  for p in [s['start'],s['end']]:coords[s['layer']].add(tuple(round(x,6) for x in p))
 for v in vias:
  for l in d['layers']:coords[l].add(tuple(round(x,6) for x in v['xy']))
 for f in d['footprints'].values():
  for p in f['pads']:
   if p['net']!=net:continue
   for l in (d['layers'] if '*.Cu' in p['layers'] else [x for x in p['layers'] if x.endswith('.Cu')]):coords[l].add(tuple(p['xy']))
 for s in seg:
  l=s['layer'];line=LineString([s['start'],s['end']]);pts=sorted([p for p in coords[l] if line.distance(Point(p))<1e-5],key=lambda p:line.project(Point(p)))
  for a,b in zip(pts,pts[1:]):G.add_edge((l,*a),(l,*b),weight=math.dist(a,b),width=s['width'],line=s['line'],kind='segment')
 for v in vias:
  a=tuple(round(x,6) for x in v['xy']); ls=[l for l in d['layers'] if (l,*a) in G]
  for l in ls[1:]:G.add_edge((ls[0],*a),(l,*a),weight=0,kind='via',line=v['line'])
 for ref,num,p in [(ref1,num1,p1),(ref2,num2,p2)]:
  node=f'{ref}.{num}';G.add_node(node);g=padshape(p)
  for l in (d['layers'] if '*.Cu' in p['layers'] else [x for x in p['layers'] if x.endswith('.Cu')]):
   for pt in coords[l]:
    if g.buffer(1e-5).covers(Point(pt)) and (l,*pt) in G:G.add_edge(node,(l,*pt),weight=math.dist(p['xy'],pt),kind='in_pad')
 try:
  pp=nx.shortest_path(G,f'{ref1}.{num1}',f'{ref2}.{num2}',weight='weight');es=[G[a][b] for a,b in zip(pp,pp[1:])]
  return {'net':net,'from':f'{ref1}.{num1}','to':f'{ref2}.{num2}','length_mm':round(sum(e['weight'] for e in es),4),'via_transitions':sum(e['kind']=='via' for e in es),'min_track_width':min([e['width'] for e in es if e['kind']=='segment'],default=None),'path':pp,'lines':[e['line'] for e in es if 'line' in e]}
 except nx.NetworkXNoPath:return {'net':net,'from':f'{ref1}.{num1}','to':f'{ref2}.{num2}','note':'No trace-centerline-only path: may use copper fill or intermediate pads.'}

if __name__=='__main__':
 data={}
 for nm,rev in [('power','P5R3'),('power','P5R5'),('imu','P5R2'),('imu','P5R4'),('rear','P5R2'),('rear','P5R4')]:
  _,d=get_board(nm,rev);out={}
  if nm=='power':
   for k in [60,70]:
    U=f'U{k}';out[U]={}
    for ref,n1,n2 in [(f'C{k+1}',3,1),(f'C{k+2}',6,1),(f'C{k+2}',2,2),(f'L{k}',2,1),(f'R{k}',4,2),(f'R{k+1}',4,1),(f'C{k+5}',4,2)]:
     out[U][ref]=path_metrics(d,U,n1,ref,n2)
   for net in ['/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT']:
    ss=[s for s in d['segments'] if s['net']==net];out[net]={'length':round(sum(math.dist(s['start'],s['end']) for s in ss),4),'vias':sum(v['net']==net for v in d['vias']),'widths':sorted(set(s['width'] for s in ss)),'segments':ss}
  elif nm=='imu':
   for a,b,c,e in [('U1',8,'C1',1),('U1',8,'C2',1),('U1',5,'C3',1),('U1',1,'R1',1),('U1',6,'C1',2),('U1',6,'C3',2),('C1',2,'C2',2)]:out[f'{a}.{b}->{c}.{e}']=path_metrics(d,a,b,c,e)
  elif nm=='rear':
   for a,b,c,e in [('USB1','B5','D3',1),('D3',1,'J2',4),('D1',1,'J2',1),('D1',1,'F1',2),('D1',1,'C1',1)]:out[f'{a}.{b}->{c}.{e}']=path_metrics(d,a,b,c,e)
  data[f'{nm}_{rev}']=out
  print(nm,rev)
  for k,v in out.items():
   if k.startswith('U60') or k.startswith('U70'):
    for kk,vv in v.items():print(k,kk,{i:j for i,j in vv.items() if i not in ['path','lines']})
   else:print(k,{i:j for i,j in v.items() if i not in ['segments','path','lines']})
 (OUT/'metrics.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
