"""Joint OV/EN transfer revision; preserves every ground via and supply corridor.

The existing EN transfer moves (+0.225,+0.010) mm to open a real reference/copper
corridor beside J105. Its three branches are rebuilt explicitly. No acceptance
is implied until native refill and all supply/reference checks pass.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R155J-plan.json').read_text());assert p['board_sha256']==c.sha
p['revision']='R155K';p['scope']=__doc__
net='Net-(U801-EN{slash}UVLO)';v='2cbd8da3-1aa1-4191-ac7a-f6145206f86e'
p['move_vias']=[{'uuid':v,'source_expected':via_snapshot(c.board,c.by_id[v]),'position_mm':[39.225,24.81],'reason':'Open the left In3 corridor while retaining physical pad spacing to R801/R802; all EN branches replaced explicitly.'}]
for id_ in ['4c63f8b0-a118-459b-b767-a13727a07ad3','9660f691-928a-44f8-a5fd-52c0cf5d70ca','829970f2-c2e5-49dc-9a0a-f5332c139165','b781f2c2-bbc5-4344-964b-649ef37c71f9']:
 t=c.by_id[id_];p['delete_copper'].append(id_)
 p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['routes'] += [
 {'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[40.8,23.8],[39.79,24.81],[39.225,24.81]]},
 {'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[39.225,24.81],[39.5,25.3]]},
 {'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[39.225,24.81],[39.775,24.025]]}]
ov='Net-(U1301-INB-_{slash}_OV)'
for r in p['routes']:
 if r['net']!=ov:continue
 pts=r['points_mm']
 if r['layer']=='In3.Cu' and pts[0]==[40.75,26.8]:r['points_mm']=[[40.75,26.8],[39.1,26.8],[38.45,26.15],[38.45,24.65],[38.8,23.95]]
 elif r['layer']=='B.Cu' and pts[-1]==[39.1,17.5]:pts[-1]=[39.2,17.4]
 elif r['layer']=='In3.Cu' and pts[0]==[39.1,17.5]:r['points_mm']=[[39.2,17.4],[39.05,17.75]]+pts[3:]
for q in p['vias']:
 if q['position_mm']==[39.1,17.5]:q['position_mm']=[39.2,17.4]
out=b/'R155K-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R155K','source':c.sha}))
