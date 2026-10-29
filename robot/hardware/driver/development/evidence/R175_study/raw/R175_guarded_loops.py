"""Compare local loop proposals while reserving actual wide supply paths.

No board is changed. Source power reservations only add search obstacles.
Existing ground vias may be reused; actual native validation remains mandatory.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R174_restore_loops.py').read_text()
src=src.replace('import ast,json,sys,time','import ast,json,math,sys,time')
src=src.replace("rev+'-restore-loops'","rev+'-R175-guarded-loops'")
old="tasks=[('ina_bypass_gnd','C1701.2','U1701.8'),('rlimit_direct_gnd','R1701.1','U1701.8'),('ina_limit','R1701.2','U1701.3'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1'),"
new="tasks=[('ina_bypass_gnd','C1701.2','U1701.8'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1'),('ina_limit','R1701.2','U1701.3'),('rlimit_direct_gnd','R1701.1','U1701.8'),"
assert src.count(old)==1; src=src.replace(old,new)
old='rows=[];newroutes=[];newvias=[];geometries={}'
new=old+'''
reserve_rows=[]
for file in ['R175-power-spines.json','R175-power-spines-v2.json']:
 data=json.loads((b/file).read_text()); assert data['source_sha256']==c.sha
 reserve_rows.extend(r for r in data['results'] if r['status']=='RESERVATION')
assert {r['name'] for r in reserve_rows}=={'ups_central','ups_right','3v3_upper','3v3_lower'}
reserves=[(r,LineString(r['points_mm']).buffer(r['preserved_width_mm']/2)) for r in reserve_rows]
'''
assert src.count(old)==1;src=src.replace(old,new)
old='  blocked[k]=unary_union([blocked[k]]+extra)'
new="  extra += [g.buffer(p.internal_clearance+p.width/2+.002) for r,g in reserves if r['layer']==ly and r['net']!=net]\n"+old
assert src.count(old)==1;src=src.replace(old,new)
old=' vf=original_vf & ~mask(unary_union(via_block),p.xx,p.yy)'
new=" via_block += [g.buffer(p.internal_clearance+.252) for r,g in reserves if r['net']!=net]\n"+old
assert src.count(old)==1;src=src.replace(old,new)
old=" if result is None or result['status']!='PROPOSAL':"
assert src.count(old)==1;src=src.replace(old," same_face_result=result\n if True:")
old=' reused=[]'
new=" if same_face_result and same_face_result['status']=='PROPOSAL':\n  if result['status']!='PROPOSAL' or same_face_result['length_mm']<=result['length_mm']+.5*len(result['vias']):result=same_face_result\n reused=[]"
assert src.count(old)==1;src=src.replace(old,new)
old="scope=__doc__,source_sha256=c.sha"
src=src.replace(old,"scope='R175 supply-reserved local loop proposals; not adopted or native-qualified',power_reservations=reserve_rows,source_sha256=c.sha")
old="dict(name=name,result={k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']},"
new="dict(name=name,result={k:v for k,v in result.items() if k not in ['routes','activate_pth_layers','vias']},"
assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,str(__file__),'exec'))
