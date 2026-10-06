from analyze import *
OUT=Path('/mnt/data/latest_review_work/evidence')
REV={'power':('P5R3','P5R5'),'motion':('P5R3','P5R5'),'imu':('P5R2','P5R4'),'rear':('P5R2','P5R4')}
def signature(x,exclude=('line','endline','uuid')):
 return json.dumps({k:v for k,v in x.items() if k not in exclude},sort_keys=True)
def cmp(nm,r0,r1):
 b0,o=get_board(nm,r0);b1,n=get_board(nm,r1)
 edits={}
 for k in ['segments','vias']:
  a=collections.Counter(signature(x) for x in o[k]);b=collections.Counter(signature(x) for x in n[k]);edits[k]={'old_count':len(o[k]),'new_count':len(n[k]),'removed':[json.loads(x) for x in (a-b).elements()],'added':[json.loads(x) for x in (b-a).elements()]}
 edits['placements']=[];edits['pin_changes']=[];edits['value_changes']=[]
 for r in sorted(set(o['footprints'])|set(n['footprints'])):
  f=o['footprints'].get(r);g=n['footprints'].get(r)
  if not f or not g:edits['placements'].append({'ref':r,'old':f,'new':g});continue
  if f['at']!=g['at'] or f['side']!=g['side']:edits['placements'].append({'ref':r,'old':[f['at'],f['side']],'new':[g['at'],g['side']]})
  if f['properties']['Value']!=g['properties']['Value']:edits['value_changes'].append([r,f['properties']['Value'],g['properties']['Value']])
  a=sorted((p['num'],p['net']) for p in f['pads']);b=sorted((p['num'],p['net']) for p in g['pads'])
  if a!=b:edits['pin_changes'].append({'ref':r,'old':a,'new':b})
 # summaries
 for b,d in [(b0,o),(b1,n)]:
  d['board_outline']=[x for x in d['drawings'] if val(x,'layer')=='Edge.Cuts']
  d['silkscreen']=[]
  for x in sub(b,'gr_text'):
   if val(x,'layer') in ['F.SilkS','B.SilkS']:
    d['silkscreen'].append({'text':x[1],'at':one(x,'at')[1:],'layer':val(x,'layer'),'line':x.line,'node':x})
  for r,f in d['footprints'].items():
   for x in sub(f['node'],'property')+sub(f['node'],'fp_text'):
    if val(x,'layer') not in ['F.SilkS','B.SilkS'] or val(x,'hide')=='yes' or 'hide' in x: continue
    if x[0]=='property':text=x[2]
    else:text=x[2]
    d['silkscreen'].append({'text':text,'ref':r,'at':one(x,'at')[1:],'layer':val(x,'layer'),'line':x.line})
  nets=collections.defaultdict(lambda:{'length':0,'segments':0,'vias':0,'widths':set(),'layers':set()})
  for s in d['segments']:
   e=nets[s['net']];e['length']+=math.dist(s['start'],s['end']);e['segments']+=1;e['widths'].add(s['width']);e['layers'].add(s['layer'])
  for v in d['vias']:nets[v['net']]['vias']+=1
  for e in nets.values():e['widths']=sorted(e['widths']);e['layers']=sorted(e['layers']);e['length']=round(e['length'],4)
  d['net_metrics']=dict(nets)
  (OUT/f'{nm}_{d["revision"]}_parsed.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 edits['silkscreen']={'old':o['silkscreen'],'new':n['silkscreen']}
 edits['net_metrics']={'old':o['net_metrics'],'new':n['net_metrics']}
 return edits
if __name__=='__main__':
 results={}
 for nm,(r0,r1) in REV.items():
  e=cmp(nm,r0,r1);results[nm]=e
  print(nm,r0,'->',r1)
  for k in ['segments','vias']:print(k, e[k]['old_count'],e[k]['new_count'],'-',len(e[k]['removed']),'+',len(e[k]['added']))
  print('moved',e['placements']);print('value changes',e['value_changes']);print('pin changes',e['pin_changes'])
  print('silk',len(e['silkscreen']['old']),len(e['silkscreen']['new']),[(x['text'],x['layer']) for x in e['silkscreen']['new']])
 (OUT/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
