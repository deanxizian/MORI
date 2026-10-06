import re,math,json,collections,hashlib
from pathlib import Path
class Node(list):
 def __init__(self,line):super().__init__();self.line=line;self.endline=line

def parse(path):
 text=Path(path).read_text(); stack=[]; root=None
 nl=[m.start() for m in re.finditer('\n',text)]
 import bisect
 for m in re.finditer(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+',text):
  t=m.group();ln=bisect.bisect_right(nl,m.start())+1
  if t=='(':
   n=Node(ln)
   if stack:stack[-1].append(n)
   else:root=n
   stack.append(n)
  elif t==')':stack.pop().endline=ln
  elif t.startswith('"'):
   try:v=json.loads(t)
   except:v=t[1:-1]
   stack[-1].append(v)
  else:
   try:v=float(t) if any(c in t for c in '.eE') else int(t)
   except:v=t
   stack[-1].append(v)
 return root

def sub(n,k):return [x for x in n if isinstance(x,list) and x and x[0]==k]
def one(n,k,default=None):return next(iter(sub(n,k)), default if default is not None else [])
def val(n,k,default=None):
 a=one(n,k);return a[1] if len(a)>1 else default

def rot(x,y,ang):
 a=math.radians(ang);return (x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a))
def transform(f,x,y):
 a=one(f,'at');dx,dy=rot(x,y,a[3] if len(a)>3 else 0);return(round(a[1]+dx,6),round(a[2]+dy,6))

def get_board(name):
 p=Path(f'/mnt/data/MORI_{name}_P5R2.kicad_pcb');b=parse(p)
 out={'name':name,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'layers':[x[1] for x in one(b,'layers')[1:] if str(x[1]).endswith('.Cu')], 'setup':one(b,'setup'),'footprints':{},'segments':[],'vias':[],'zones':[],'drawings':[]}
 for f in sub(b,'footprint'):
  props={x[1]:x[2] for x in sub(f,'property')};ref=props.get('Reference','?')
  fd={'ref':ref,'lib':f[1], 'at':one(f,'at')[1:],'side':val(f,'layer'),'properties':props,'pads':[],'graphics':[x for x in f if isinstance(x,list) and x[0].startswith('fp_')], 'line':f.line,'endline':f.endline, 'paste_override':one(f,'solder_paste_margin')[1:]}
  for pd in sub(f,'pad'):
   pos=one(pd,'at')[1:];xy=transform(f,*pos[:2]); net=one(pd,'net');net=net[-1] if net else ''
   fd['pads'].append({'num':str(pd[1]),'type':pd[2],'shape':pd[3],'xy':xy,'angle':pos[2] if len(pos)>2 else 0,'local':pos,'size':one(pd,'size')[1:],'drill':one(pd,'drill')[1:],'layers':one(pd,'layers')[1:],'net':net,'line':pd.line,'endline':pd.endline,'node':pd})
  out['footprints'][ref]=fd
 for s in sub(b,'segment'):
  out['segments'].append({'start':one(s,'start')[1:],'end':one(s,'end')[1:],'width':val(s,'width'),'layer':val(s,'layer'),'net':one(s,'net')[-1], 'line':s.line,'uuid':val(s,'uuid')})
 for s in sub(b,'via'):
  out['vias'].append({'xy':one(s,'at')[1:],'size':val(s,'size'),'drill':val(s,'drill'),'net':one(s,'net')[-1] if one(s,'net') else '', 'layers':one(s,'layers')[1:],'line':s.line, 'uuid':val(s,'uuid')})
 for s in sub(b,'zone'):
  out['zones'].append({'net':one(s,'net')[-1] if one(s,'net') else '', 'layer':val(s,'layer'),'name':val(s,'name'),'keepout':one(s,'keepout'),'outline':one(s,'polygon'), 'filled':sub(s,'filled_polygon'),'line':s.line})
 for k in ['gr_line','gr_rect','gr_arc','gr_text']:out['drawings']+=sub(b,k)
 return b,out

if __name__=='__main__':
 for nm in ['rear','imu']:
  b,d=get_board(nm)
  Path(f'/mnt/data/mori_rear_imu_review/{nm}_parsed.json').write_text(json.dumps(d,indent=2,ensure_ascii=False))
  print('\nBOARD',nm,d['layers'],len(d['footprints']),'components',len(d['segments']),'segments',len(d['vias']),'vias')
  for x in d['drawings']:
   if val(x,'layer')=='Edge.Cuts' or x[0]=='gr_text':print('drawing', x)
  for r,f in sorted(d['footprints'].items()):
   print(r, f['properties'].get('Value'), f['at'], f['side'],f'Lines {f["line"]}-{f["endline"]}')
   for p in f['pads']:print(' ',p['num'],p['xy'],p['size'],p['angle'],p['net'])
  print('zones',[(z['name'],z['net'],z['layer'],len(z['filled']),z['line']) for z in d['zones']])
  print('Vias',d['vias'])
