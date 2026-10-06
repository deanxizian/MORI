"""Current GB823 M2 screws: PH1 catalogue blade and conservative full handle."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from interface_completion import axial
load_collections();COLS['DATUMS'].hide_viewport=False;assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
stages={r['id']:r for r in json.loads((HERE/'bench_sequence_checks.json').read_text())['fasteners']};results=[]
rows=list(P['interface_completion']['inserts'])
if P.get('assembly_issue_fixes',{}).get('enabled'):
 fasteners={r['id']:r for r in json.loads((HERE/'fastener_current.json').read_text())}
 for n in [v.replace('_Nut','_Screw') for v in P['assembly_issue_fixes']['drive_nuts']['ids']]:
  f=fasteners[n];a=np.array(f['extracted_axis_outward']);bearing=np.array(f['tool_start_mm'])-a*f['nominal_head_height_mm']
  rows.append(dict(screw=n,outward=a.tolist(),screw_head_bearing_mm=bearing.tolist(),head_height_mm=1.4,screw_length_mm=8))
for r in rows:
 if not r.get('screw_length_mm'):continue
 n=r['screw'];a=np.array(r['outward']);face=np.array(r['screw_head_bearing_mm'])+a*r['head_height_mm'];bench=stages[n]['included_parts'];trials=[]
 for sku,length,total in [('Wiha 42415',60,160),('Wiha 42416',80,180)]:
  shapes=[('blade',axial(2,length,face+a*(.03+length/2),a)),('handle_max_envelope',axial(9,total-length,face+a*(.03+length+(total-length)/2),a))];hits=[]
  for label,m in shapes:
   bb=np.array(m.bounding_box())
   for k in bench:
    if k==n or k not in ss:continue
    s=ss[k]
    if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
    v=max(0,(m^s.m).volume())
    if v>.02:hits.append({'tool_piece':label,'part':k,'mm3':v})
  trials.append({'sku':sku,'blade_mm':[4,length],'handle_max_mm':[18,total-length],'hits':hits})
 results.append({'screw':n,'stage':stages[n]['stage'],'status':'PASS' if any(not t['hits'] for t in trials) else 'FAIL','trials':trials})
out={'status':'FAIL' if any(r['status']=='FAIL' for r in results) else 'PASS','source_blend_sha256':hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),'recess':'GB823 M2 No.1 per cited screw manufacturer table; not a PH0 assumption','tool_source':'https://wiha.com/tools/screwdrivers/precision-screwdrivers/picofinish/phillips/picofinish-fine-screwdriver/42415','screw_source':P['interface_completion']['M2_screw_source'],'rows':results,'limits':'Catalogue4mm round blade /18mm maximum handle diameter, handle length from total minus exposed blade. Full cylinders are conservative envelopes; exact shaped tip and hand grip/force not modeled. Rigid staged clearance only, no physical torque qualification.'}
(HERE/'catalogue_driver_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('CATALOGUE_DRIVER',out['status'],len(results),[(r['screw'],r['trials'][-1]['hits']) for r in results if r['status']=='FAIL'],flush=True)
