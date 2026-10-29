from pathlib import Path
import json
p=Path('robot/.state/c3-completion/trials');j=json.loads((p/'R134L-plan.json').read_text());g=next(v for v in j['vias'] if v['net']=='GND');assert g['position_mm']==[62.9,14.5];g['position_mm']=[63,14.55];j['ground_stitch_adjustment']={'from_screened_pre_layout_mm':[62.9,14.5],'final_mm':[63,14.55],'reason':'Increase lower F/In3 transfer margin to project 2 mm proximity screen; native keepout, physical clearance and post-refill power regression still required.'};(p/'R134L-final-plan.json').write_text(json.dumps(j,indent=2)+'\n')
