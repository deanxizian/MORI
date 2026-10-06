"""Nominal two-segment shell service candidates with explicit prerequisites."""
import sys,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
data=json.loads((HERE/'body_seam_candidate.json').read_text());results=[]
for keep_rear in [False,True]:
 moving=['Body_Upper']+[n for n in ss if n.startswith(('Frame_Insert','Shell_Insert'))]
 if keep_rear:moving += [n for n in ss if n.startswith(('Rear_Interface','USB_Receptacle','Power_Switch'))]
 removed=[n for n in data['removed_first'] if n not in moving];fixed={n:s for n,s in ss.items() if n not in removed+moving}
 def test(t):
  for n in moving:
   m=ss[n].m.translate(t);bb=np.array(m.bounding_box())
   for k,s in fixed.items():
    if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
    v=max(0,(m^s.m).volume())
    if v>.05:return [n,k,v]
  return None
 for dy in [-4,-6,-8,-10,-12]:
  for lift in [0,1,2]:
   hit=None
   for u in np.linspace(0,1,abs(dy)*4+1):
    if (a:=test([0,dy*u,lift*u])):hit={'phase':'shift','fraction':float(u),'hit':a};break
   if not hit:
    for dz in np.arange(lift,120.01,.5):
     if (a:=test([0,dy,dz])):hit={'phase':'lift','z':float(dz),'hit':a};break
   results.append({'rear_PCB_retained_on_shell':keep_rear,'shift_y_mm':dy,'initial_lift_mm':lift,'status':'FAIL' if hit else 'PASS','first_hit':hit})
 print('BODY_SERVICE',keep_rear,[(r['shift_y_mm'],r['initial_lift_mm'],r['status']) for r in results if r['rear_PCB_retained_on_shell']==keep_rear],flush=True)
(HERE/'body_seam_service.json').write_text(json.dumps({'rows':results,'source':'body_seam_candidate.blend','limits':'Nominal0.25mm initial shift and0.5mm lift samples; shell-mounted speaker and head/bridge must be removed first. Prerequisite paths/tools remain separate.'},indent=2))
