"""Joint D3 plus all three CLR branches, with explicit removal of dangling stubs.
This is an independent candidate, not an adopted change. ADC and FAULT still
require complete restoration and all regression checks before adoption.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
base=Path('robot/.state/c3-completion/trials')
src=base/'R138B';c=Copper(src/'MORI_Interface_C3.kicad_pcb')
rows=json.loads((base/'R138B-joint-search/searches.json').read_text())
d3='Net-(U1001-D3_{slash}_current_ADC)';adc='/01 {slash} Core/ACT_CURRENT_ADC'
plan={'revision':'R138C','board_sha256':c.sha,'scope':__doc__,'delete_copper':[
 '40ba9c33-421b-4bc2-aaa0-c3ddc317a380','f4966ca0-550f-4c37-ae36-5f587849fb8c',
 '2e91ec62-054b-49d4-887e-e72b2d32a10e','c97f1777-11f8-4527-ba17-02832261c855',
 'c016adf7-1b9e-4da6-9d31-bfa4b5752db8','c74cd486-ee0e-4fbb-97e7-6701087a2826'],
 'deleted_copper_expected':{},'routes':[],'vias':[]}
for u in plan['delete_copper']:
 t=c.by_id[u];assert type(t).__name__=='PCB_TRACK'
 plan['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
def add(net,points):plan['routes'].append({'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':points})
# Inspect simple alternatives before retaining a constrained curved-obstacle path.
p=Planner(str(src/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu'],.2)
free,vf,blocked,allowed=p.geometry(d3)
variants=[
 [[30.15,6.8875],[30.15,6.1],[28.7,6.1],[27.45,7.35],[27.45,8.2],[26.2,9.45],[26.2,11.9],[26.8,12.5],[27.6,12.5],[28.025,12.075],[28.6,12.075]],
 [[30.15,6.8875],[30.15,6.1],[28.7,6.1],[27.45,7.35],[27.45,8.2],[26.2,9.45],[26.2,11.9],[26.7,12.4],[26.8,12.4],[26.9,12.5],[27.6,12.5],[28.025,12.075],[28.6,12.075]],
]
checks=[]
for points in variants:
 line=LineString(points)
 checks.append({'points_mm':points,'blocked_intersection_length_mm':line.intersection(blocked[0]).length,'reference_uncovered_length_mm':line.difference(allowed[0]).length})
valid=next((v for v in checks if v['blocked_intersection_length_mm']<1e-8 and v['reference_uncovered_length_mm']<1e-8),None)
if valid:add(d3,valid['points_mm'])
else:
 r=next(r for r in rows if r['net']==d3)['result'];assert r['status']=='PROPOSAL'
 plan['routes'].extend({'net':d3,**x} for x in r['routes'])
add('/CLR_N',[[29.4,9.8],[29.4,13.4625],[29.9375,14],[30.4,14]])
add('/CLR_N',[[27.4,13.8],[28.05,14.45],[29.1,14.45],[29.55,14],[29.9375,14]])
add('/CLR_N',[[24.76,9.61],[26.02,8.35],[26.65,8.35],[26.8,8.2],[26.8,7.5]])
r=next(r for r in rows if r['net']==adc and r['groups']==[['J101.7'],['R1033.2']])['result'];assert r['status']=='PROPOSAL'
plan['routes'].extend({'net':adc,**x} for x in r['routes'])
for name,obj in [('R138C-plan.json',plan),('R138C-d3-smoothing.json',checks)]:
 f=base/name;assert not f.exists();f.write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({'routes':len(plan['routes']),'deleted_segments':len(plan['delete_copper']),'simplified_d3_selected':valid is not None}))
