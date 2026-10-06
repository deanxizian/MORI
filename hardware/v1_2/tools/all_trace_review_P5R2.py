#!/usr/bin/env python3
"""Complete copper inventory and net-by-net review atlas; KiCad Python.

Screening flags are candidates, never automatic approval of routing style.
Original P5/P5R1 projects are immutable inputs. No manufacturing export.
"""
from pathlib import Path
import pcbnew as k
import json, math, hashlib, shutil, sys, collections, csv, html, subprocess
from layout_P5 import xy, pt, mm, F, B, rect

H=Path(__file__).resolve().parents[1]; ROOT=H.parents[1]; O=H/'layout_P5R2'
KINDS=['motion','imu','power','rear']
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
NODE='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
SHARP='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paths(kind):
 n=f'MORI_{kind}_P5R2';d=H/'kicad'/n;r=O/'reports'/kind;r.mkdir(parents=True,exist_ok=True)
 return n,d,d/(n+'.kicad_pcb'),r
def source(kind):
 n=f'MORI_{kind}_'+('P5R1' if kind=='motion' else 'P5');d=H/'kicad'/n
 return n,d,d/(n+'.kicad_pcb')
def init():
 log={}
 for kind in KINDS:
  sn,sd,sp=source(kind);n,d,p,r=paths(kind)
  if d.exists():raise RuntimeError('Refusing to overwrite '+str(d))
  for f in sd.rglob('*'):
   if not f.is_file() or f.name.startswith('~') or f.suffix in ['.lck','.kicad_prl','.ses','.dsn']:continue
   rel=f.relative_to(sd);to=d/rel.parent/f.name.replace(sn+'.',n+'.');to.parent.mkdir(parents=True,exist_ok=True);data=f.read_bytes()
   if f.suffix in ['.kicad_pro','.kicad_sch']:data=data.replace(sn.encode(),n.encode())
   to.write_bytes(data)
  log[kind]={'source':str(sp.relative_to(ROOT)),'sha256':sha(sp),'candidate':str(p.relative_to(ROOT))}
 (O/'sources.json').write_text(json.dumps(log,indent=2)+'\n')
def segment_distance(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];q=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/q)) if q else 0
 return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
def extract(kind,phase):
 n,d,p,r=paths(kind)
 if phase=='before':_,_,p=source(kind)
 b=k.LoadBoard(str(p));tracks=[];vias=[];pads=[];fps=[]
 for f in b.GetFootprints():
  fps.append({'ref':f.GetReference(),'value':f.GetValue(),'rect':rect(f),'xy':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'layer':b.GetLayerName(f.GetLayer())})
  for pad in f.Pads():
   sz=pad.GetSize();pads.append({'ref':f.GetReference()+'.'+pad.GetNumber(),'net':pad.GetNetname(),'xy':xy(pad.GetPosition()),'size':xy(sz),'angle':pad.GetOrientationDegrees(),'through':pad.IsOnLayer(F) and pad.IsOnLayer(B),'layers':[b.GetLayerName(l) for l in [F,B] if pad.IsOnLayer(l)]})
 for t in b.GetTracks():
  uid=t.m_Uuid.AsString()
  if isinstance(t,k.PCB_VIA):vias.append({'uuid':uid,'net':t.GetNetname(),'xy':xy(t.GetPosition()),'diameter':k.ToMM(t.GetWidth(F)),'drill':k.ToMM(t.GetDrillValue())});continue
  a,z=xy(t.GetStart()),xy(t.GetEnd());tracks.append({'uuid':uid,'net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'a':a,'z':z,'width':k.ToMM(t.GetWidth()),'length':math.dist(a,z),'flags':[]})
 groups=collections.defaultdict(list)
 for t in tracks:groups[t['net'],t['layer']].append(t)
 candidates=[]
 def flag(typ,ts,pos,detail):
  ident='C%04d'%(len(candidates)+1);candidates.append({'id':ident,'type':typ,'net':ts[0]['net'],'layer':ts[0]['layer'],'xy':pos,'uuids':[t['uuid']for t in ts],'detail':detail})
  for t in ts:t['flags'].append(ident)
 for group in groups.values():
  for i,t in enumerate(group):
   a,z=t['a'],t['z'];dx,dy=z[0]-a[0],z[1]-a[1]
   if t['length']<.25:flag('SHORT_SEGMENT',[t],a,{'length_mm':t['length']})
   if min(abs(dx),abs(dy))>.001 and abs(abs(dx)-abs(dy))>.002:flag('NON_45',[t],a,{'delta_mm':[dx,dy]})
   for u in group[:i]:
    near=[(math.dist(v,w),v,w) for v in [a,z] for w in [u['a'],u['z']] if .00001<math.dist(v,w)<.16]
    if near:flag('OFFSET_ENDPOINTS',[t,u],min(near)[1],{'minimum_mm':min(near)[0]})
    dx2,dy2=u['z'][0]-u['a'][0],u['z'][1]-u['a'][1]
    if t['length']<.01 or u['length']<.01:continue
    if abs(dx*dy2-dy*dx2)/(t['length']*u['length'])<.0001:
     distance=abs(dx*(u['a'][1]-a[1])-dy*(u['a'][0]-a[0]))/t['length']
     projected=sorted(((v[0]-a[0])*dx+(v[1]-a[1])*dy)/t['length']for v in [u['a'],u['z']]);overlap=min(t['length'],projected[1])-max(0,projected[0])
     if overlap>.1 and distance<(t['width']+u['width'])/2-.001:flag('OVERLAP_PARALLEL',[t,u],a,{'separation_mm':distance,'overlap_mm':overlap})
  nodes=collections.defaultdict(list)
  for t in group:
   for v in [t['a'],t['z']]:nodes[tuple(v)].append(t)
  for v,ts in nodes.items():
   if len(ts)!=2:continue
   ends=[t['z'] if tuple(t['a'])==v else t['a'] for t in ts];lengths=[math.dist(e,v)for e in ends]
   if min(lengths)<.001:continue
   dot=sum((ends[0][j]-v[j])*(ends[1][j]-v[j])for j in range(2))/(lengths[0]*lengths[1])
   if dot>.05:flag('FOLDBACK',[*ts],v,{'angle_degrees':math.degrees(math.acos(min(1,dot)))})
 stats={'segments':len(tracks),'vias':len(vias),'nets_with_tracks':len({t['net']for t in tracks}),'length_mm':sum(t['length']for t in tracks),'flags':dict(collections.Counter(c['type']for c in candidates))}
 result={'kind':kind,'phase':phase,'pcb':str(p.relative_to(ROOT)),'sha256':sha(p),'stats':stats,'tracks':tracks,'vias':vias,'pads':pads,'footprints':fps,'candidates':candidates}
 (r/f'{phase}_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with (r/f'{phase}_all_segments.csv').open('w',newline='')as f:
  fields=list(tracks[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(tracks)
 print(kind,phase,stats,flush=True);return result
def picture(data,net):
 ts=[t for t in data['tracks']if t['net']==net];vs=[v for v in data['vias']if v['net']==net];ps=[p for p in data['pads']if p['net']==net]
 coords=[p for t in ts for p in [t['a'],t['z']]]+[p['xy']for p in ps]+[v['xy']for v in vs]
 x1=min(p[0]for p in coords)-2;y1=min(p[1]for p in coords)-2;x2=max(p[0]for p in coords)+2;y2=max(p[1]for p in coords)+2
 w,h=x2-x1,y2-y1
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x1} {y1} {w} {h}" width="1000" height="600">',f'<rect x="{x1}" y="{y1}" width="{w}" height="{h}" fill="#10161e"/>']
 for f in data['footprints']:
  rc=f['rect']
  if not rc:continue
  a,b,c,d=rc
  s.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="none" stroke="#697482" stroke-width=".055"/>')
  if f['ref']!='U100':s.append(f'<text x="{(a+c)/2}" y="{(b+d)/2}" fill="#858d98" font-size=".48" text-anchor="middle">{f["ref"]}</text>')
 for t in sorted(data['tracks'],key=lambda t:t['net']==net):
  own=t['net']==net;col=('#ef5555'if t['layer']=='F.Cu'else'#46a9ec')if own else'#28333e'
  a,z=t['a'],t['z'];s.append(f'<path d="M{a[0]} {a[1]} L{z[0]} {z[1]}" fill="none" stroke="{col}" stroke-width="{t["width"]}" stroke-linecap="round"><title>{html.escape(t["uuid"]+" "+t["net"]+" "+str(t["width"]))}</title></path>')
 for p in data['pads']:
  own=p['net']==net;x,y=p['xy'];sx,sy=p['size'];color='#eed681'if own else'#535b66'
  s.append(f'<g transform="translate({x},{y}) rotate({-p["angle"]})"><rect x="{-sx/2}" y="{-sy/2}" width="{sx}" height="{sy}" rx=".12" fill="none" stroke="{color}" stroke-width=".075"/></g>')
  if own:s.append(f'<text x="{x+.15}" y="{y-.38}" fill="#fff1b5" font-size=".55">{html.escape(p["ref"])}</text>')
 for v in vs:
  x,y=v['xy'];s.append(f'<circle cx="{x}" cy="{y}" r="{v["diameter"]/2}" fill="none" stroke="#ddb0fa" stroke-width=".1"/><circle cx="{x}" cy="{y}" r="{v["drill"]/2}" fill="#10161e"/>')
 s.append('</svg>');return ''.join(s)
def atlas(kind,phase):
 _,_,_,r=paths(kind);data=json.loads((r/f'{phase}_inventory.json').read_text());out=O/'atlas'/phase/kind;out.mkdir(parents=True,exist_ok=True)
 nets=sorted({t['net']for t in data['tracks']}|{p['net']for p in data['pads']if p['net'] and 'unconnected-'not in p['net']})
 pages=[];index=[]
 for i,net in enumerate(nets):
  path=out/f'{i+1:03d}.svg';s=picture(data,net);path.write_text(s);index.append({'number':i+1,'net':net,'svg':str(path.relative_to(O))})
 for page in range(math.ceil(len(nets)/6)):
  body=['<svg xmlns="http://www.w3.org/2000/svg" width="2200" height="2220" viewBox="0 0 2200 2220"><rect width="2200" height="2220" fill="#10161e"/>']
  for j in range(6):
   i=page*6+j
   if i>=len(nets):break
   net=nets[i];x=(j%2)*1100;y=(j//2)*740
   body.append(f'<text x="{x+20}" y="{y+30}" fill="white" font-family="sans-serif" font-size="24">{i+1:03d} {kind} {html.escape(net)}</text>')
   s=(out/f'{i+1:03d}.svg').read_text().replace('width="1000" height="600"',f'x="{x+10}" y="{y+45}" width="1080" height="680"')
   body.append(s)
  body.append('</svg>');svg=out/f'page_{page+1:02d}.svg';png=svg.with_suffix('.png');svg.write_text(''.join(body))
  js='require('+json.dumps(SHARP)+')(process.argv[1]).png().toFile(process.argv[2]);'
  subprocess.run([NODE,'-e',js,str(svg),str(png)],check=True,capture_output=True);pages.append(str(png.relative_to(O)))
 (r/f'{phase}_atlas_index.json').write_text(json.dumps({'nets':index,'pages':pages},indent=2)+'\n')
 print(kind,phase,'atlas pages',len(pages),flush=True)
if __name__=='__main__':
 action=sys.argv[1]
 if action=='init':init()
 else:
  phase=sys.argv[2];kinds=sys.argv[3:] or KINDS
  for kind in kinds:
   if action=='inventory':extract(kind,phase)
   elif action=='atlas':atlas(kind,phase)
   else:raise SystemExit(action)
