"""Reconstruct an explicit single plan from R134N to the screened R141I study.

This does not copy a study into the development entry. Every retained native
object is checked first; final acceptance requires a fresh build from the
canonical source, native checks and the independent planned-delta review.
"""
import json
import sys
from pathlib import Path
from shapely.affinity import rotate,translate
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *

b=Path('robot/.state/c3-completion/trials')
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(b/'R141I/MORI_Interface_C3.kicad_pcb')
assert a.sha=='0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
assert c.sha=='5112d5301af2d9ae89d8a31efb147cc2b500970bae088fda7630b20c4911bdc3'
af={f.GetReference():f for f in a.footprints};cf={f.GetReference():f for f in c.footprints}
assert set(af)==set(cf)
moves=[];guard_deltas=[]
for ref,old in sorted(af.items()):
 new=cf[ref]
 assert old.GetLayer()==new.GetLayer() and old.GetValue()==new.GetValue() and old.GetFPID().GetUniStringLibId()==new.GetFPID().GetUniStringLibId()
 if xy(old.GetPosition())==xy(new.GetPosition()) and old.GetOrientationDegrees()==new.GetOrientationDegrees():continue
 delta=[round(y-x,6) for x,y in zip(xy(old.GetPosition()),xy(new.GetPosition()))]
 spec={'reference':ref,'from_mm':list(xy(old.GetPosition())),'delta_mm':delta,'rotation_deg':new.GetOrientationDegrees()}
 owned=[k for k in a.keepouts if k['name'].startswith('BODY_'+ref+'_')]
 assert owned and not any('_VIA_' in k['name'] for k in owned), 'Dedicated fixed-cutout consolidation needed for '+ref
 ck={k['id']:k for k in c.keepouts}
 for k in owned:
  expected=translate(rotate(k['shape'],-(new.GetOrientationDegrees()-old.GetOrientationDegrees()),origin=xy(old.GetPosition())),xoff=delta[0],yoff=delta[1])
  difference=expected.symmetric_difference(ck[k['id']]['shape']).area
  assert difference<1e-7,(ref,k['id'],difference)
  guard_deltas.append({'reference':ref,'uuid':k['id'],'symmetric_difference_mm2':difference})
 moves.append(spec)
removed=[];snapshots={}
for old in a.tracks:
 u=uid(old);new=c.by_id.get(u)
 if new is None:
  assert type(old).__name__=='PCB_TRACK'
  removed.append(u);snapshots[u]={'net':old.GetNetname(),'layer':a.board.GetLayerName(old.GetLayer()),'width_mm':old.GetWidth()/1e6,'start_mm':list(xy(old.GetStart())),'end_mm':list(xy(old.GetEnd()))}
 else:
  assert type(old).__name__==type(new).__name__ and old.GetNetname()==new.GetNetname()
  for layer in LAYERS:assert a.shapes.get((u,layer),GeometryCollection()).symmetric_difference(c.shapes.get((u,layer),GeometryCollection())).area<1e-8,(u,layer)
  if isinstance(old,pcb.PCB_VIA):assert via_snapshot(a.board,old)==via_snapshot(c.board,new)
vias=[];routes=[];mapping=[]
for v in sorted(c.vias,key=uid):
 if uid(v) in a.by_id:continue
 assert v.GetViaType()==pcb.VIATYPE_THROUGH
 widths={v.GetWidth(c.ids[l])/1e6 for l in LAYERS};assert len(widths)==1
 vias.append({'net':v.GetNetname(),'position_mm':list(xy(v.GetPosition())),'diameter_mm':widths.pop(),'drill_mm':v.GetDrillValue()/1e6})
 mapping.append({'kind':'via','study_uuid':uid(v),'plan_index':len(vias)-1})
for t in sorted(c.segments,key=uid):
 if uid(t) in a.by_id:continue
 assert type(t).__name__=='PCB_TRACK'
 routes.append({'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'points_mm':[list(xy(t.GetStart())),list(xy(t.GetEnd()))]})
 mapping.append({'kind':'route','study_uuid':uid(t),'plan_index':len(routes)-1})
plan={'revision':'R142','board_sha256':a.sha,
      'purpose':'Independent development candidate: connect ADC D3 and its public trunk while preserving all original nets; explicitly reroute CLR, FAULT, U1401 OUT, supply/ground bridges and R903 ARMED escape. Published R108P and mechanical adoption unchanged. Full board and physical qualification incomplete.',
      'study_source_sha256':c.sha,'translations':moves,'delete_copper':sorted(removed),'deleted_copper_expected':snapshots,'vias':vias,'routes':routes}
review={'scope':__doc__,'source_sha256':a.sha,'study_sha256':c.sha,'moves':moves,'guard_transform_checks':guard_deltas,'removed_source_tracks':len(removed),'new_vias':len(vias),'new_segments':len(routes),'study_to_plan_mapping':mapping}
for name,data in [('R142-plan.json',plan),('R142-consolidation-review.json',review)]:
 with (b/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in review.items() if k!='study_to_plan_mapping'},indent=2))
