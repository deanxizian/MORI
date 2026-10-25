"""Bounded auxiliary JSON. Commands additionally use the MORI/2 contract validator."""
import json

def object_json(raw, maximum=4096):
 if len(raw.encode('utf-8') if isinstance(raw,str) else raw)>maximum:raise ValueError('LENGTH')
 def pairs(items):
  out={}
  for key,value in items:
   if key in out:raise ValueError('DUPLICATE_KEY')
   out[key]=value
  return out
 def nonfinite(_):raise ValueError('NONFINITE')
 try:result=json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
 except (RecursionError,TypeError) as error:raise ValueError('JSON') from error
 if not isinstance(result,dict):raise ValueError('OBJECT_REQUIRED')
 return result
