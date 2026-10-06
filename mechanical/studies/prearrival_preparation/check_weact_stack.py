"""Read-only rigid stack-height screening; not a socket selection or PCB edit."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
from native_electronics import board_transform
ROOT=PROJECT
load_collections();assembled();bpy.context.view_layer.update()
ids={r['id'] for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text()) if r['group'] not in ('coupon','dock')}
targets={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids if bpy.data.objects.get(PREFIX+n) and n not in ['MCU_Motion','MCU_Carrier']}
core=Solid(bpy.data.objects[PREFIX+'MCU_Motion'])
c=json.loads((ROOT/P['native_electronics']['boards']['motion']['mesh']).read_text());r,t=board_transform('motion',c)
native=[]
for comp in c['components']:
 if comp['reference'] in ['PCB','U100']:continue
 for so in comp['solids']:
  vv=np.array(so['vertices_mm'])@r.T+t;ff=np.array(so['triangles'],dtype=np.uint64)
  mm=manifold.Manifold(manifold.Mesh64(vv,ff))
  if mm.status()==manifold.Error.NoError:native.append((comp['reference'],mm))
rows=[]
for stack in np.arange(6,11.01,.5):
 m=core.m.translate([0,0,float(stack-6)]);bb=np.array(m.bounding_box());hits=[]
 for n,s in targets.items():
  if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
  v=max(0,(m^s.m).volume())
  if v>.02:hits.append({'part':n,'overlap_mm3':round(v,4)})
 for n,s in native:
  b=np.array(s.bounding_box())
  if np.any(bb[3:]<b[:3]) or np.any(b[3:]<bb[:3]):continue
  v=max(0,(m^s).volume())
  if v>.02:hits.append({'part':'MCU_Carrier/'+n,'overlap_mm3':round(v,4)})
 rows.append({'nominal_board_stack_mm':round(float(stack),2),'core_rigid_shift_z_mm':round(float(stack-6),2),'status':'PASS' if not hits else 'FAIL','overlaps':hits})
report={'baseline':P['revision'],'status':'PASS','native_board_changed':False,'main_geometry_changed':False,'rows':rows,'scope':'Original WeAct full CAD/proxy rigid shift against current solids and other native carrier components; soldered module pins intentionally pass through PCB holes. Does not add a female socket, prove pin engagement, connector retention, hand grip, insertion travel or tolerance clearance. PASS means no sampled volume above0.02mm3, not that this stack is viable.','proposed_header_requirements':{'pitch_mm':2.54,'A_B':'two2x12','C_D':'two2x3','E':'one2x4; confirm actual population and side against received core-board configuration','native_hole_mm':1.0,'module_male_pin_length_and_female_engagement':'Manufacturer mating drawing required; do not trim or rescale unknown purchased geometry.'}}
(HERE/'weact_stack_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('WEACT_STACK_COMPLETE',[(r['nominal_board_stack_mm'],r['status'],len(r['overlaps'])) for r in rows],flush=True)
