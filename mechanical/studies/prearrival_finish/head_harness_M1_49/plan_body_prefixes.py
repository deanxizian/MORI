"""Analytic tangent body-to-neck candidate paths on unmodified current solids."""
from pathlib import Path
import sys,json,math,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from common import P
from neck_capacity import local_curves
from curvature_paths import paths
ctx=Context();start=time.time();pack,data,neckrows=local_curves(P['neck_harness_capacity'])
port='motion_J5';originals=ctx.port_pins[port]['pins'];axis=ctx.port_pins[port]['axis']
pools={};failed=collections.Counter();witness={};arrays={};trials=0
for pin,p in originals.items():
 p=np.asarray(p);pin=int(pin)
 for slot in range(7,11):
  q=data[f'wire{slot}_y0'][0];d=q[:2]-p[:2];D=float(np.linalg.norm(d));along=np.r_[d/D,0]
  pool=[]
  for lead in [5.,7.,10.]:
   a=p+axis*lead
   stem=np.linspace(p,a,math.ceil(lead/.08)+1)
   issue=ctx.clear(stem,ignore=['Plug_'+port])
   if issue:
    failed[issue['object']]+=1;witness.setdefault(issue['object'],issue);continue
   for radius in [7.,8.,10.]:
    for candidate in paths([0,a[2]],[0,1],[D,q[2]],[0,1],radius,.08):
     trials+=1;uv=candidate['points_xy_mm'];points=p+uv[:,0,None]*along
     points[:,2]=uv[:,1]
     assert np.linalg.norm(points[0]-a)<1e-7 and np.linalg.norm(points[-1]-q)<1e-7
     if candidate['analytic_length_mm']>190:failed['over190mm']+=1;continue
     hit=ctx.clear(points,chord_error=candidate['chord_error_mm'])
     if hit:
      failed[hit['object']]+=1;witness.setdefault(hit['object'],hit);continue
     curve=np.vstack([stem,points[1:]])
     cid=f'pin{pin}_slot{slot}_{len(pool)}'
     arrays[cid]=curve
     pool.append(dict(id=cid,pin=pin,port=port,slot=slot,OD_mm=.6604,lead_mm=lead,
           minimum_bend_mm=radius,analytic_length_mm=float(lead+candidate['analytic_length_mm']),chord_error_mm=candidate['chord_error_mm'],family=candidate['family'],points=len(curve),bounds_mm=[curve.min(0).tolist(),curve.max(0).tolist()]))
  pools[f'pin{pin}_slot{slot}']=sorted(pool,key=lambda x:x['analytic_length_mm'])
  print('BODY_PREFIX',pin,slot,'valid',len(pool),flush=True)
ctx.assert_unchanged()
np.savez_compressed(HERE/'body_prefix_candidates.npz',**arrays)
r=dict(status='PASS' if all(any(pools[f'pin{pin}_slot{s}'] for s in range(7,11)) for pin in range(1,5)) else 'BLOCKED',scope='Individual4-wire CAM body prefix options only; mutual packing, motion, anchors and wired installation untested',sources=ctx.sources,trials=trials,pools=pools,fail_counts=dict(failed),first_failure_witness=witness,curve_sha256=sha(HERE/'body_prefix_candidates.npz'),source_script_sha256=sha(Path(__file__)),main_changed=False,full_harness='BLOCKED',elapsed_s=time.time()-start)
(HERE/'body_prefix_screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('BODY_PREFIX_SCREEN',r['status'],len(arrays),dict(failed),flush=True)
