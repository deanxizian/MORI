import sys,json,math,collections,time
sys.path.insert(0,'/mnt/data/latest_review_work')
from analyze import *
sys.path.append('/mnt/data/latest_review_work/legacy')
from geometry import objects,padshape
from shapely.strtree import STRtree
import networkx as nx
OUT=Path('/mnt/data/latest_review_work/evidence')

def analyze_geometry(d):
 oo=objects(d);g=nx.Graph();g.add_nodes_from(range(len(oo)))
 shorts=[];near=[];float_copper=[]
 for layer in d['layers']:
  ids=[i for i,o in enumerate(oo) if o['layer']==layer]; t=STRtree([oo[i]['geom'] for i in ids])
  for i in ids:
   o=oo[i]
   for jj in t.query(o['geom'].buffer(.151)):
    j=ids[int(jj)]
    if i>=j:continue
    p=oo[j];dist=o['geom'].distance(p['geom'])
    if o['net']==p['net'] and o['net']:
     if dist<1e-5:g.add_edge(i,j)
    elif o['net'] and p['net']:
     if dist<1e-5:
      area=o['geom'].intersection(p['geom']).area
      if area>1e-7:shorts.append({'a':o['label'],'b':p['label'],'nets':[o['net'],p['net']],'layer':layer,'overlap_area':area,'lines':[o['line'],p['line']]})
     if dist<.1499:near.append({'a':o['label'],'b':p['label'],'nets':[o['net'],p['net']],'layer':layer,'distance':dist,'lines':[o['line'],p['line']]})
 top_components={};local_points={}
 for layer in ['F.Cu','B.Cu']:
  for net in ['/GND','/+3V3']:
   ids=[i for i,o in enumerate(oo) if o['layer']==layer and o['net']==net]
   comps=list(nx.connected_components(g.subgraph(ids)))
   for ci,cc in enumerate(comps):
    pads=[oo[i]['label'] for i in cc if oo[i]['kind']=='pad']
    vias=[oo[i]['data']['xy'] for i in cc if oo[i]['kind']=='via']
    through=[oo[i]['data']['xy'] for i in cc if oo[i]['kind']=='pad' and oo[i]['data']['type']=='thru_hole']
    if pads:
     top_components[f'{layer}:{net}:{ci}']={'pads':pads,'vias':vias,'pth':through,'objects':len(cc)}
     pp=vias+through
     for i in cc:
      o=oo[i]
      if o['kind']=='pad':
       nearxy=min(pp,key=lambda v:math.dist(v,o['data']['xy'])) if pp else None
       local_points[f'{layer}:{o["label"]}']={'net':net,'xy':o['data']['xy'],'component':f'{layer}:{net}:{ci}','via_count':len(vias),'pth_count':len(through),'nearest_layer_connection':nearxy,'straight_distance_mm':round(math.dist(nearxy,o['data']['xy']),4) if nearxy else None}
 for kind in ['via','pad']:
  same=collections.defaultdict(list)
  for i,o in enumerate(oo):
   if o['kind']==kind:same[o['id']].append(i)
  for ids in same.values():
   for j in ids[1:]:g.add_edge(ids[0],j)
 comps=list(nx.connected_components(g));groups=collections.defaultdict(list)
 for cc in comps:
  padset=sorted({oo[i]['label'] for i in cc if oo[i]['kind']=='pad'})
  nets={oo[i]['net'] for i in cc}
  if len(nets)!=1:raise RuntimeError(nets)
  net=next(iter(nets))
  if padset:groups[net].append(padset)
  elif net and not str(net).startswith('unconnected'):float_copper.append({'net':net,'objects':[oo[i]['label'] for i in cc]})
 disconnect={k:v for k,v in groups.items() if k and not str(k).startswith('unconnected') and len(v)>1}
 cuts=[]
 netnodes=collections.defaultdict(list)
 for i,o in enumerate(oo):netnodes[o['net']].append(i)
 for vi,v in enumerate(d['vias']):
  net=v['net']; gg=g.subgraph(netnodes[net]).copy(); removed=[i for i in gg if oo[i]['kind']=='via' and oo[i]['id']==f'via{vi}'];gg.remove_nodes_from(removed)
  ccs=[]
  for cc in nx.connected_components(gg):
   ps=sorted({oo[i]['label'] for i in cc if oo[i]['kind']=='pad'})
   if ps:ccs.append(ps)
  if len(ccs)>len(groups[net]):cuts.append({'net':net,'xy':v['xy'],'size':v['size'],'drill':v['drill'],'groups':ccs,'line':v['line']})
 out={'method':'Approximate 2D stored-copper model, not native KiCad DRC; no refilling or project rules','object_count':len(oo),'shorts':shorts,'clearances_below_0p15':near,'disconnected_pad_groups':disconnect,'floating_conductor_groups':float_copper,'single_via_cuts':cuts,'local_ground_power_components':top_components,'local_pad_returns':local_points}
 return oo,g,out

if __name__=='__main__':
 for name,rev in [('power','P5R5'),('motion','P5R5'),('imu','P5R4'),('rear','P5R4')]:
  t=time.time();_,d=get_board(name,rev);oo,g,r=analyze_geometry(d)
  (OUT/f'{name}_{rev}_geometry.json').write_text(json.dumps(r,indent=2))
  print(name,rev,'objects',len(oo),'shorts',len(r['shorts']),'near',len(r['clearances_below_0p15']),'disconnect',r['disconnected_pad_groups'],'singlecuts',len(r['single_via_cuts']),'sec',round(time.time()-t,2),flush=True)
  print('shorts',r['shorts'],flush=True)
