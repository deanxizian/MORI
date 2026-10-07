"""Generate C command IDs/parameter ranges and public JSON Schema from catalogue."""
import json,pathlib
r=pathlib.Path(__file__).resolve().parent;s=json.loads((r/'command_spec.json').read_text())
lines=['/* Generated from command_spec.json by generate.py; do not edit. */','#pragma once','#include <stdbool.h>','#include <math.h>','typedef enum {']
for k,v in s['commands'].items():lines.append(f' MORI_{k}={v["code"]},')
lines+=['} mori_v1_kind_t;','static inline bool mori_v1_numeric_valid(unsigned kind,const float *p,unsigned n){',' switch(kind){']
for k,v in s['commands'].items():
 fields=list(v['fields'].values())
 if all(f['kind'] in ('number','integer') for f in fields):
  expr=[f'n=={len(fields)}']+[f'isfinite(p[{i}]) && p[{i}] >= {f["min"]:.9g}f && p[{i}] <= {f["max"]:.9g}f' for i,f in enumerate(fields)]
  # Ensure valid C decimal literals.
  import re
  expr=[re.sub(r'(?<![.\w])(-?\d+)f\b',r'\1.0f',e) for e in expr]
  lines.append(f' case MORI_{k}:return '+' && '.join(expr)+';')
lines+=[' default:return false;',' }','}']
(r/'generated/commands.h').write_text('\n'.join(lines)+'\n')
props={'protocol':{'const':s['protocol']},'type':{'enum':list(s['commands'])},'source':{'enum':s['sources']},'permissions':{'type':'array','items':{'enum':s['permissions']},'uniqueItems':True,'minItems':1},'params':{'type':'object'}}
for k in ('device_id','session_id','command_id','client_id'):props[k]={'type':'string','pattern':'^[a-zA-Z0-9_-]{1,64}$'}
for k in ('sequence','sent_at_ms','basis_device_ms','valid_for_ms'):props[k]={'type':'integer','minimum':1 if k in ['sequence','valid_for_ms'] else 0,'maximum':30000 if k=='valid_for_ms' else 2147483647 if k=='sequence' else 9007199254740991}
variants=[]
for name,v in s['commands'].items():
 pp={}
 for k,f in v['fields'].items():
  pp[k]= {'enum':f['values']} if f['kind']=='enum' else {'type':f['kind']}
  if 'min' in f:pp[k].update(minimum=f['min'],maximum=f['max'])
  if f['kind']=='string':pp[k]['maxLength']=f['max']
 variants.append({'if':{'properties':{'type':{'const':name}}},'then':{'properties':{'params':{'type':'object','properties':pp,'required':list(pp),'additionalProperties':False},'valid_for_ms':{'maximum':v['ttl_max_ms']},'permissions':{'contains':{'const':v['permission']}}}}})
(r/'command.schema.json').write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','title':'MORI/2 command','type':'object','additionalProperties':False,'required':list(props),'properties':props,'allOf':variants},indent=2)+'\n')
