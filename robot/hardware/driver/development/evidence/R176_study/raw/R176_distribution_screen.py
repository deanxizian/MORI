"""Native local loops and independent FAULT access with actual power guards.

Ground targets use explicit track/pad/via components without planes. Other
native connections are reused rather than redrawn. Proposals require native
refill, all existing electrical checks and full placement/route review.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_guarded_loops_expanded.py').read_text()
src=src.replace('import ast,json,math,sys,time','import ast,collections,copy,json,math,sys,time')
src=src.replace("rev=sys.argv[1];out=b/(rev+'-R175-guarded-loops')", "rev=sys.argv[1];mode=sys.argv[2];out=b/(rev+'-R176-'+mode)")
src=src.replace('np.arange(40,55.001,p.grid)','np.arange(30,65.001,p.grid)').replace('np.arange(5,21.001,p.grid)','np.arange(2,26.001,p.grid)')
src=src.replace("['B.Cu','F.Cu','In3.Cu','In2.Cu'],.2","['B.Cu','F.Cu','In3.Cu','In2.Cu'],.3")
src=src.replace('bounds_mm=[40,5,55,21]','bounds_mm=[30,2,65,26]')
start=src.index('tasks=[');end=src.index('\nrows=[]',start)
src=src[:start]+"tasks=[('restore_distribution','U1302.5','U301.2')]"+src[end:]

start=src.index('reserve_rows=[]');end=src.index('\nfor name,an,bn in tasks:',start)
src=src[:start]+'''
data=json.loads((b/(rev+'-power-spines.json')).read_text())
assert data['source_sha256']==c.sha
reserve_rows=data['results'];assert len(reserve_rows)==4 and all(r['status']=='RESERVATION' for r in reserve_rows)
reserves=[(r,LineString(r['points_mm']).buffer(r['preserved_width_mm']/2)) for r in reserve_rows]
from plan_existing_copper import groups
native=collections.defaultdict(list)
for (u,ly),s in c.shapes.items():native[c.by_id[u].GetNetname(),ly].append(s)
trace_only=copy.copy(c);trace_only.__dict__['copper']={key:unary_union(values) for key,values in native.items()}
endpoint_checks=[]
'''+src[end:]
old=" z=dict(pads=[bn],layers={ly:c.shapes[uid(bb),ly] for ly in p.layers if (uid(bb),ly) in c.shapes})"
new=old+'''
 native_groups=groups(trace_only if net=='GND' else c,net)
 ga=next(g for g in native_groups if an in g['pads']);gz=next(g for g in native_groups if bn in g['pads'])
 if ga is gz:
  row=dict(name=name,net=net,pads=[an,bn],result=dict(status='ALREADY_NATIVE_EXPLICIT_CONNECTED' if net=='GND' else 'ALREADY_NATIVE_CONNECTED'),elapsed_seconds=time.monotonic()-start)
  rows.append(row);print(json.dumps(row),flush=True);continue
 a=ga;z=gz
'''
assert src.count(old)==1;src=src.replace(old,new)
old=' if net not in geometries:geometries[net]=p.geometry(net)'
new='''
 if net not in geometries:
  saved=p.via_common
  if net=='GND':
   common=[s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
   common.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'])
   common.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias)
   common.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0)
   p.via_common=unary_union(common)
  geometries[net]=p.geometry(net);p.via_common=saved
'''
assert src.count(old)==1;src=src.replace(old,new)
src=src.replace(" if net=='GND':vf=np.zeros_like(vf)", " # Native geometric constraints also permit additional GND vias.")
src=src.replace("  assert not actual or net!='GND'", "  assert all(v['diameter_mm']==.5 and v['drill_mm']==.3 for v in actual)")
old="scope='R175 supply-reserved local loop proposals; not adopted or native-qualified'"
src=src.replace(old,"scope='R176 native explicit targets and verified supply reservations; not adopted'")
exec(compile(src,str(__file__),'exec'))
