"""Move one OV transfer and the proposed FAULT transfer as a coupled corridor study."""
from pathlib import Path
import json,sys
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R165I-plan.json').read_text());rev='R165J'
p['revision']=rev;p['scope']=__doc__+' Keep the U1501-to-C1501 B-face filter path. Move the original OV through via from (54.4,31.8) to (55.9,33.9) and the new FAULT transfer to (54.3,33.9), freeing the In3 corridor between two existing 3V3 vias. Restore every native power/reference connection before acceptance. UV/FAULT still unfinished.'
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');u='52ba2607-8ec1-4960-af4d-8852674d6048';v=c.by_id[u]
p['move_vias'].append({'uuid':u,'source_expected':via_snapshot(c.board,v),'position_mm':[55.9,33.9],'reason':'Joint OV/FAULT transfer arrangement opens the UV In3 corridor while preserving original filter B connection and both existing 3V3 vias. Replaces the planned In2 OV segment explicitly; all reference and native power gates remain required.'})
v=next(v for v in p['vias'] if v['net']=='/FAULT_N' and v['position_mm']==[55.9,33.9]);v['position_mm']=[54.3,33.9]
r=next(r for r in p['routes'] if r['net']=='/FAULT_N' and r['layer']=='B.Cu' and r['points_mm'][0]==[55.9,33.9]);r['points_mm']=[[54.3,33.9],[54.05,34.15],[53.4,34.15]]
net='Net-(U1501-INB-_{slash}_OV)'
r=next(r for r in p['routes'] if r['net']==net and r['layer']=='In2.Cu' and r['points_mm'][0]==[54.4,31.8]);r['points_mm']=[[55.9,33.9],[55.9,33.2],[56.4,32.7],[58,32.7],[58.375,33.075],[58.375,34.25]]
p['routes'].append({'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[55.35,32.375],[55.9,32.925],[55.9,33.9]]})
with (b/(rev+'-plan.json')).open('x') as f:json.dump(p,f,indent=2);f.write('\n')
