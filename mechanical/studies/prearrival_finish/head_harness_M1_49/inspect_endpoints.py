"""Capture present native pins and planning breakpoints without changing geometry."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from neck_capacity import local_curves
from common import P
ctx=Context();pack,data,rows=local_curves(P['neck_harness_capacity'])
ports={}
for name in ['motion_J5','power_J9','power_J18']:
 p=ctx.port_pins[name];s=ctx.plug[name]
 ports[name]=dict(axis=p['axis'].tolist(),exit_face_mm=p['exit_face'].tolist(),pins={str(k):v.tolist() for k,v in p['pins'].items()},housing_bounds_mm=[s.lo.tolist(),s.hi.tolist()],evidence='Native PCB pin centers projected to nominal mate allocation; actual crimp exits pending')
parts={n:dict(group=s.group,bounds_mm=[s.lo.tolist(),s.hi.tolist()]) for n,s in ctx.ss.items() if n in ['Yaw_Servo','Pitch_Servo','CAM_Mainboard','Display_PCB','Camera_PCB','Speaker','Power_Module','MCU_Carrier','Load_Frame','Yaw_Reaction_Link','Yaw_Base','Pitch_Yoke']}
ends=[dict(id=i,OD_mm=r['OD_mm'],angle_deg=r['angle_deg'],body_end_mm=data[f'wire{i}_y0'][0].tolist(),yaw_end_mm=data[f'wire{i}_y0'][-1].tolist(),electrical_assignment=None) for i,r in enumerate(pack['selected'])]
ctx.assert_unchanged()
r=dict(revision=P['revision'],status='PASS',scope='Current native endpoint and local planning-breakpoint inventory only',sources=ctx.sources,ports=ports,parts=parts,neck_endpoints=ends,full_harness='BLOCKED',supplier_cut_lengths_released=False,physical_validation='NOT_TESTED')
(HERE/'endpoints.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'ports':ports,'parts':parts,'neck_endpoints':ends},ensure_ascii=False,indent=2),flush=True)
