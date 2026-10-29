"""Target the six links disrupted/newly accessible in the R161E joint layout.
This does not repeat unchanged all-board searches. Proposals need native refill,
all power/reference checks and real path/body/manufacturer-layout review.
"""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R161E-restore-search';out.mkdir(exist_ok=False)
p=Planner(str(b/'R161E/MORI_Interface_C3.kicad_pcb'),.1,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2)
requests=[
 ('uv_divider','Net-(U1301-INA+_{slash}_UV)','R1302.1','U1301.3'),
 ('uv_filter','Net-(U1301-INA+_{slash}_UV)','C1301.1','U1301.3'),
 ('ov_upstream','Net-(U1301-INB-_{slash}_OV)','R1306.1','U1301.4'),
 ('fault_restore','/FAULT_N','U1301.6','U1501.1'),
 ('uv_output','/13 {slash} Head_Fault_Delay/HEAD_UV_N','U1301.1',None),
 ('bias_enable','/HEAD_UV_ENABLE','R1311.2','Q1701.1'),
]
cache={};results=[]
for name,net,a,bpad in requests:
 print(json.dumps({'request':name,'phase':'geometry'}),flush=True);start=time.monotonic()
 if net not in cache:cache[net]=(p.routing_groups(net),p.geometry(net))
 gs,geom=cache[net];ga=next(g for g in gs if a in g['pads'])
 if bpad is None:
  others=[g for g in gs if g is not ga];assert len(others)==1
  gb=others[0]
 else:gb=next(g for g in gs if bpad in g['pads'])
 if ga is gb:r={'status':'ALREADY_CONNECTED'}
 else:r=p.solve(ga,gb,geom,300000)
 row={'request':name,'net':net,'from_pad':a,'to_pad':bpad,'groups':[ga['pads'],gb['pads']],**r,'elapsed_seconds':time.monotonic()-start}
 if r['status']=='PROPOSAL':
  plan={'revision':'R161E-'+name,'board_sha256':p.c.sha,'scope':__doc__,
   'routes':[{**q,'net':net} for q in r['routes']], 'vias':[{**q,'net':net} for q in r['vias']],
   'activate_pth_layers':r['activate_pth_layers'],'search_grid_mm':.1,'source_request':name,'adoption_prohibited':True}
  (out/(name+'-plan.json')).write_text(json.dumps(plan,indent=2)+'\n')
 results.append(row);(out/'searches.json').write_text(json.dumps({'source_sha256':p.c.sha,'scope':__doc__,'results':results},indent=2)+'\n')
 print(json.dumps({k:v for k,v in row.items() if k not in ['routes','groups','vias','activate_pth_layers']}),flush=True)
