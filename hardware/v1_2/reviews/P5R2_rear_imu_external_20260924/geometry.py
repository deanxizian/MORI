from analyze import *
import shapely
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.strtree import STRtree
import networkx as nx
import html

OUT=Path('/mnt/data/mori_rear_imu_review')
def padshape(p,expand=0):
 w,h=p['size']; w+=2*expand;h+=2*expand
 if p['shape']=='circle':g=Point(0,0).buffer(w/2,resolution=32)
 elif p['shape']=='oval':
  r=min(w,h)/2
  a=(max(w-h,0)/2,max(h-w,0)/2)
  g=LineString([(-a[0],-a[1]),a]).buffer(r,resolution=32) if max(a)>0 else Point(0,0).buffer(r,resolution=32)
 elif p['shape']=='roundrect':
  r=val(p['node'],'roundrect_rratio',0.25)*min(p['size'])+expand
  r=min(r,min(w,h)/2)
  g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r,resolution=16)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p['angle'],origin=(0,0)),*p['xy'])

def objects(d):
 out=[];n=0
 for r,f in d['footprints'].items():
  for i,p in enumerate(f['pads']):
   if p['type']=='np_thru_hole':continue
   layers=d['layers'] if '*.Cu' in p['layers'] else [l for l in p['layers'] if l.endswith('.Cu')]
   for l in layers:out.append({'kind':'pad','label':f'{r}.{p["num"]}','id':f'{r}.{i}','net':p['net'],'layer':l,'geom':padshape(p),'line':p['line'],'data':p})
 for i,v in enumerate(d['vias']):
  for l in d['layers']:out.append({'kind':'via','label':f'via{i}@{v["xy"]}','id':f'via{i}','net':v['net'],'layer':l,'geom':Point(v['xy']).buffer(v['size']/2,resolution=32),'line':v['line'],'data':v})
 for i,s in enumerate(d['segments']):out.append({'kind':'segment','label':f'seg{i}','id':f'seg{i}','net':s['net'],'layer':s['layer'],'geom':LineString([s['start'],s['end']]).buffer(s['width']/2,resolution=16),'line':s['line'],'data':s})
 for i,z in enumerate(d['zones']):
  for j,p in enumerate(z['filled']):
   pts=[a[1:] for a in one(p,'pts')[1:]];g=Polygon(pts)
   if not g.is_valid:g=g.buffer(0)
   out.append({'kind':'zone','label':f'zone{i}.{j}','id':f'zone{i}.{j}','net':z['net'],'layer':val(p,'layer',z['layer']),'geom':g,'line':z['line'],'data':z})
 return out

def connect(d):
 oo=objects(d);g=nx.Graph();g.add_nodes_from(range(len(oo)));shorts=[];near=[]
 for layer in d['layers']:
  ids=[i for i,o in enumerate(oo) if o['layer']==layer]; shapes=[oo[i]['geom'] for i in ids];t=STRtree(shapes)
  for ii,i in enumerate(ids):
   o=oo[i]
   for jj in t.query(o['geom'].buffer(.21)):
    j=ids[int(jj)]
    if i>=j:continue
    p=oo[j];dist=o['geom'].distance(p['geom'])
    if o['net']==p['net'] and o['net']:
     if dist<1e-5:g.add_edge(i,j)
    elif o['net'] and p['net']:
     ar=o['geom'].intersection(p['geom']).area
     record={'a':o['label'],'b':p['label'],'nets':[o['net'],p['net']],'layer':layer,'distance':dist,'area':ar,'lines':[o['line'],p['line']]}
     if ar>1e-7:shorts.append(record)
     if dist <.15-1e-5:near.append(record)
 for kind in ['pad','via']:
  groups=collections.defaultdict(list)
  for i,o in enumerate(oo):
   if o['kind']==kind:groups[o['id']].append(i)
  for ids in groups.values():
   for i in ids[1:]:g.add_edge(ids[0],i)
 comp=list(nx.connected_components(g));disconnect={};
 for net in sorted(set(o['net'] for o in oo if o['net'] and not o['net'].startswith('unconnected'))):
  ccs=[]
  for cc in comp:
   pads=sorted(set(oo[i]['label'] for i in cc if oo[i]['kind']=='pad' and oo[i]['net']==net))
   if pads:ccs.append(pads)
  if len(ccs)>1:disconnect[net]=ccs
 result={'objects':len(oo),'shorts':shorts,'clearances_below_0p15':near,'disconnected_pad_groups':disconnect}
 # Remove each via (all layers) to find cutsets of named pads.
 bridges=[]
 for vnum,v in enumerate(d['vias']):
  ids=[i for i,o in enumerate(oo) if o['id']==f'via{vnum}' and o['kind']=='via'];gg=g.copy();gg.remove_nodes_from(ids)
  ccs=[]
  for cc in nx.connected_components(gg):
   pads=sorted(set(oo[i]['label'] for i in cc if oo[i]['kind']=='pad' and oo[i]['net']==v['net']))
   if pads:ccs.append(pads)
  if len(ccs)>1:bridges.append({'net':v['net'],'xy':v['xy'],'size':v['size'],'drill':v['drill'],'groups':ccs})
 result['single_via_cuts']=bridges
 return oo,g,result

def render(d,oo,layer):
 from xml.sax.saxutils import escape
 w,h=(24,25) if d['name']=='rear' else (20,16)
 color={'/GND':'#cedbcc','/VBUS_RAW':'#f37935','/VBUS_FUSED':'#cc3b36','/CC1':'#008fc4','/CC2':'#943ec4','/MASTER_RETURN':'#ad8550','/LOOP_3V3':'#447c44','/CLR_N':'#3c53a0','/+3V3':'#d0433a','/MISO_IC':'#663ac0','/MISO':'#814ec6','/SCK':'#227bbb','/MOSI':'#00a08d','/DRDY':'#b07720','/CS_N':'#d05092'}
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{int((w+4)*50)}" height="{int((h+6)*50)}" viewBox="-2 -3 {w+4} {h+6}">',f'<rect x="-2" y="-3" width="{w+4}" height="{h+6}" fill="white"/>',f'<text x="0" y="-1.4" font-size="0.65" font-family="Arial">{d["name"].upper()} | {layer} | top-view coordinates (mm)</text>',f'<rect width="{w}" height="{h}" fill="#f8fafc" stroke="#111" stroke-width="0.07"/>']
 def geo(g,c,opacity=1):
  if g.geom_type=='Polygon':
   path=' '.join('M'+' L'.join(f'{x:.5f},{y:.5f}' for x,y in ring.coords)+' Z' for ring in [g.exterior,*g.interiors])
   s.append(f'<path d="{path}" fill="{c}" opacity="{opacity}" fill-rule="evenodd"/>')
  elif hasattr(g,'geoms'):
   for gg in g.geoms:geo(gg,c,opacity)
 for kind in ['zone','segment','via','pad']:
  for o in oo:
   if o['kind']==kind and o['layer']==layer:geo(o['geom'],color.get(o['net'],'#777'),.75 if kind=='zone' else 1)
 for r,f in d['footprints'].items():
  if f['side']!=layer and not r.startswith('H'):continue
  for a in f['graphics']:
   if val(a,'layer')!=layer.replace('.Cu','.Fab'):continue
   pts=[]
   if a[0] in ['fp_line','fp_rect']:
    p1=one(a,'start')[1:];p2=one(a,'end')[1:]
    if a[0]=='fp_line':pts=[p1,p2]
    else:pts=[p1,[p2[0],p1[1]],p2,[p1[0],p2[1]],p1]
   elif a[0]=='fp_poly':pts=[p[1:] for p in one(a,'pts')[1:]];pts.append(pts[0])
   if pts:
    at=f['at'];pp=[]
    for x,y in pts:
     x,y=rot(x,y,at[2] if len(at)>2 else 0);pp.append((x+at[0],y+at[1]))
    s.append('<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pp)+'" fill="none" stroke="#282c34" stroke-width=".055"/>')
  at=f['at'];s.append(f'<text x="{at[0]}" y="{at[1]-.45}" text-anchor="middle" font-family="Arial" font-size=".48" font-weight="bold">{escape(r)}</text>')
 for f in d['footprints'].values():
  for p in f['pads']:
   if p['type']!='smd':
    drill=p['drill'];dia=drill[-1] if drill else 0
    if isinstance(dia,(int,float)) and dia>0:
     x,y=p['xy'];s.append(f'<circle cx="{x}" cy="{y}" r="{dia/2}" fill="white" stroke="#42464c" stroke-width=".03"/>')
   if layer in p['layers'] or '*.Cu' in p['layers']:
    x,y=p['xy'];s.append(f'<text x="{x}" y="{y+.10}" font-family="Arial" text-anchor="middle" font-size=".28" fill="#111">{escape(p["num"])}</text>')
 for v in d['vias']:
  x,y=v['xy'];s.append(f'<circle cx="{x}" cy="{y}" r="{v["drill"]/2}" fill="white"/>')
 for xx in range(0,w+1,5):s.append(f'<text x="{xx}" y="{h+1}" font-family="Arial" font-size=".36">{xx}</text>')
 for yy in range(0,h+1,5):s.append(f'<text x="-1.4" y="{yy+.15}" font-family="Arial" font-size=".36">{yy}</text>')
 s.append('</svg>');fout=OUT/f'{d["name"]}_{layer}.svg';fout.write_text('\n'.join(s))
 import cairosvg
 cairosvg.svg2png(url=str(fout),write_to=str(fout.with_suffix('.png')))
if __name__=='__main__':
 for nm in ['rear','imu']:
  _,d=get_board(nm);oo,g,res=connect(d)
  (OUT/f'{nm}_geometry.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
  print(nm,json.dumps(res,indent=2))
  for l in d['layers']:render(d,oo,l)
