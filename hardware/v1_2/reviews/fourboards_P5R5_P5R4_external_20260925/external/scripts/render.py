from analyze import *
from run_geometry import objects
from shapely.geometry import box,Point,LineString
from xml.sax.saxutils import escape
import cairosvg
OUT=Path('/mnt/data/latest_review_work/figures')
COLORS={'/GND':'#d6dfd5','/+3V3':'#ba2439','/M5_VIN':'#be3436','/C5_VIN':'#be3436','/M5_SW':'#ce8b19','/C5_SW':'#ce8b19','/M5_BOOT':'#a846c0','/C5_BOOT':'#a846c0','/M5_FB':'#2377b2','/C5_FB':'#2377b2','/+5V_MOTION':'#438c57','/+5V_CAM':'#438c57','/M5_EN':'#777777','/C5_EN':'#777777','/BAT_REV':'#3e6991','/BAT_MON':'#b95416','/KELVIN_P':'#962180','/KELVIN_N':'#009c90','/VBUS_RAW':'#d53e2a','/VBUS_FUSED':'#b46318','/CC1':'#0d739d','/CC2':'#953bb1','/MISO_IC':'#8b55b1','/MISO':'#8b55b1','/SCK':'#1f77b4','/MOSI':'#1f8e78','/CS_N':'#cc5786','/DRDY':'#9b7923'}

def draw(d,oo,layer,bounds,name=None,labels=True,padnets=False,selected=None):
 xmin,ymin,xmax,ymax=bounds;w=xmax-xmin;h=ymax-ymin
 border=box(*bounds)
 name=name or d['name']+'_'+d['revision']+'_'+layer.replace('.','_')
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{min(1800,int((w+2)*65))}" height="{min(1800,int((w+2)*65))*(h+2)/(w+2):.0f}" viewBox="{xmin-1} {ymin-1} {w+2} {h+2}">',f'<rect x="{xmin-1}" y="{ymin-1}" width="{w+2}" height="{h+2}" fill="#ffffff"/>',f'<rect x="{xmin}" y="{ymin}" width="{w}" height="{h}" fill="#fafbfd" stroke="#222" stroke-width=".045"/>',f'<text x="{xmin}" y="{ymin-.35}" font-family="sans-serif" font-size=".38">{escape(name)} | coordinates in mm, viewed from top</text>']
 def geom(g,c,op=1):
  if g.is_empty:return
  if g.geom_type=='Polygon':
   path=' '.join('M'+' L'.join(f'{x:.5f},{y:.5f}' for x,y in ring.coords)+' Z' for ring in [g.exterior,*g.interiors]);s.append(f'<path d="{path}" fill="{c}" opacity="{op}" fill-rule="evenodd"/>')
  elif hasattr(g,'geoms'):
   for gg in g.geoms:geom(gg,c,op)
 for kind in ['zone','segment','via','pad']:
  for o in oo:
   if o['kind']==kind and o['layer']==layer and o['geom'].intersects(border):
    c=COLORS.get(o['net'],'#848a98');op=(.82 if kind=='zone' else 1) if not selected or o['net'] in selected else .2
    geom(o['geom'].intersection(border),c,op)
 for r,f in d['footprints'].items():
  if f['side']!=layer and not any(p['type']=='thru_hole' for p in f['pads']):continue
  for a in f['graphics']:
   if val(a,'layer') not in [layer.replace('.Cu','.Fab')]:continue
   pts=[]
   if a[0] in ['fp_line','fp_rect']:
    p1=one(a,'start')[1:];p2=one(a,'end')[1:]
    pts=[p1,p2] if a[0]=='fp_line' else [p1,[p2[0],p1[1]],p2,[p1[0],p2[1]],p1]
   elif a[0]=='fp_poly':pts=[p[1:] for p in one(a,'pts')[1:]];pts.append(pts[0])
   if pts:
    at=f['at'];pp=[]
    for x,y in pts:
     x,y=rot(x,y,at[2] if len(at)>2 else 0);pp.append((x+at[0],y+at[1]))
    if box(min(x for x,y in pp),min(y for x,y in pp),max(x for x,y in pp),max(y for x,y in pp)).intersects(border):
     s.append('<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in pp)+'" fill="none" stroke="#363b44" stroke-width=".038"/>')
  x,y=f['at'][:2]
  if labels and xmin<=x<=xmax and ymin<=y<=ymax:
   s.append(f'<text x="{x}" y="{y-.22}" text-anchor="middle" font-family="sans-serif" font-size=".38" font-weight="bold" fill="#111">{escape(r)}</text>')
 for f in d['footprints'].values():
  for p in f['pads']:
   x,y=p['xy'];
   if not xmin<=x<=xmax or not ymin<=y<=ymax:continue
   if p['type']!='smd':
    dia=p['drill'][-1] if p['drill'] else 0
    if isinstance(dia,(int,float)) and dia>0:s.append(f'<circle cx="{x}" cy="{y}" r="{dia/2}" fill="white" stroke="#555" stroke-width=".02"/>')
   if layer in p['layers'] or '*.Cu' in p['layers']:
    txt=p['num']+(' '+p['net'].lstrip('/') if padnets else '')
    s.append(f'<text x="{x}" y="{y+.085}" font-family="sans-serif" text-anchor="middle" font-size=".20" fill="#111">{escape(txt)}</text>')
 for v in d['vias']:
  x,y=v['xy']
  if xmin<=x<=xmax and ymin<=y<=ymax:s.append(f'<circle cx="{x}" cy="{y}" r="{v["drill"]/2}" fill="white"/>')
 step=5 if w>20 else 2
 for x in range(math.ceil(xmin),math.floor(xmax)+1):
  if x%step==0:s.append(f'<text x="{x}" y="{ymax+.5}" font-family="sans-serif" font-size=".25">{x}</text>')
 for y in range(math.ceil(ymin),math.floor(ymax)+1):
  if y%step==0:s.append(f'<text x="{xmin-.65}" y="{y+.08}" font-family="sans-serif" font-size=".25">{y}</text>')
 s.append('</svg>');fn=OUT/(name+'.svg');fn.write_text('\n'.join(s));cairosvg.svg2png(url=str(fn),write_to=str(fn.with_suffix('.png')))
 return fn

if __name__=='__main__':
 for nm,rev in [('power','P5R5'),('imu','P5R4'),('rear','P5R4')]:
  _,d=get_board(nm,rev);oo=objects(d)
  if nm=='power':
   for l in ['F.Cu','B.Cu','In1.Cu','In2.Cu']:draw(d,oo,l,(19,20,33,34),'power_U60_'+l.replace('.','_'),padnets=l=='F.Cu')
   for l in ['F.Cu','B.Cu']:draw(d,oo,l,(19,34,33,48),'power_U70_'+l.replace('.','_'),padnets=l=='F.Cu')
   draw(d,oo,'F.Cu',(24,8,40,20),'power_Kelvin',padnets=True)
  else:
   for l in d['layers']:draw(d,oo,l,(0,0,20,16) if nm=='imu' else (0,0,24,25),padnets=True)
