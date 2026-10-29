"""Native same-face-input group, retaining every still-legal original segment.

Rebuild from accepted R168G. The selected complete group is a finite placement
proposal, not acceptance. One non-ground 3V3 transfer is retired only with the
existing exact contact/island proof, and the lower transfer is relocated after
native pad/body/reference screening. All source GND vias and rules stay fixed.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.affinity import rotate,translate,scale
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import move_body_guards,set_outline,point_mm
from plan_layered_route import mask
b=Path('robot/.state/c3-completion/trials');rev='R176A';out=b/(rev+'-plan.json');assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');t=Copper(c.path)
assert c.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
screen=json.loads((b/'R174-expanded-placement.json').read_text());assert screen['source_sha256']==c.sha
chosen=screen['solutions'][8];fps={f.GetReference():f for f in t.footprints}
assert all(r['face']=='B.Cu' for r in chosen['parts'] if r['reference'] in ['U1701','R1706','R1707'])
plan=dict(revision=rev,scope=__doc__,board_sha256=c.sha,translations=[],delete_copper=[],deleted_copper_expected={},move_vias=[],remove_obsolete_vias=[],vias=[],routes=[])
for row in chosen['parts']:
 ref=row['reference'];f=fps[ref];old=list(xy(f.GetPosition()));angle=f.GetOrientationDegrees();face=t.board.GetLayerName(f.GetLayer())
 new=row['position_mm'];a=row['rotation_deg'];delta=[round(new[i]-old[i],6) for i in range(2)]
 if old==new and int(angle)%360==a and face==row['face']:continue
 spec=dict(reference=ref,from_mm=old,delta_mm=delta,rotation_deg=a)
 owned=[z for z in t.zones if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_'+ref+'_')]
 reconstruct=any('_VIA_' in z.GetZoneName() for z in owned)
 if reconstruct:spec.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True,repartition_fixed_via_guards=True)
 assert face==row['face'],'This same-face-input candidate requires no side changes'
 move_body_guards(owned,delta,reconstruct,a-angle,old,reconstruct,reconstruct)
 f.SetOrientationDegrees(a);f.Move(point_mm(delta));plan['translations'].append(spec)
 for p in f.Pads():assert list(xy(p.GetPosition()))==row['pads'][p.GetNumber()]['position_mm']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
retiring='aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57';moving='c89d9b75-62b7-4bdc-8fe8-09516366b58c'
prospective=set(screen['prospectively_retired_tracks'])|set(chosen['additional_track_dependencies'])
# Every original lead touching the retiring transfer must be explicitly handled.
retire_leads={uid(tt) for tt in c.segments if tt.GetNetname()==c.by_id[retiring].GetNetname() and c.shapes[uid(tt),c.board.GetLayerName(tt.GetLayer())].intersects(c.shapes[retiring,c.board.GetLayerName(tt.GetLayer())])}
prospective |= retire_leads
checks=[]
for u in sorted(prospective):
 tt=c.by_id[u];ly=c.board.GetLayerName(tt.GetLayer());g=c.shapes[u,ly];net=tt.GetNetname();reasons=[]
 if u in retire_leads:reasons.append('lead_to_retiring_3V3_transfer')
 if any(g.distance(shape(p,t.ids[ly]))<.1999996-1e-9 for p in t.pads if p.IsOnLayer(t.ids[ly]) and p.GetNetname()!=net):reasons.append('new_foreign_pad_clearance')
 if any(g.intersection(k['shape']).area>1e-8 for k in t.keepouts if k['tracks'] and ly in k['layers']):reasons.append('transformed_native_track_keepout')
 for f in t.footprints:
  if f.GetLayer()!=t.ids[ly]:continue
  body=fab(f).difference(unary_union([shape(p,t.ids[ly]) for p in f.Pads()]))
  if g.intersection(body).area>1e-8:reasons.append('own_face_body_'+f.GetReference())
 checks.append(dict(uuid=u,net=net,retired=bool(reasons),reasons=reasons))
 if reasons:
  plan['delete_copper'].append(u)
  plan['deleted_copper_expected'][u]=dict(net=net,layer=ly,width_mm=tt.GetWidth()/1e6,start_mm=list(xy(tt.GetStart())),end_mm=list(xy(tt.GetEnd())))
oldspec=next(x for x in json.loads((b/'R171E-plan.json').read_text())['remove_obsolete_vias'] if x['uuid']==retiring)
oldspec['reason']='Explicitly replace the original F/B VS leads and retire this non-ground transfer: native In2 fill touches only this via, while In3 remains a real supply region. The moved INA300 group conflicts with the old site; all retained anchors, original supplies and power widths still require restoration and native checks.'
assert oldspec['source_expected']==via_snapshot(c.board,c.by_id[retiring])
removal=obsolete_via_removal_check(c.board,c.by_id[retiring],oldspec,plan['delete_copper'])
assert removal['allowed'],removal
plan['remove_obsolete_vias']=[oldspec]
excluded=set(plan['delete_copper'])|{retiring,moving}
references=[c.shapes[uid(tt),c.board.GetLayerName(tt.GetLayer())].intersection(c.copper.get(('GND',REFERENCE[c.board.GetLayerName(tt.GetLayer())]),GeometryCollection())) for tt in c.segments if uid(tt) not in excluded and tt.GetNetname()!='GND' and c.board.GetLayerName(tt.GetLayer()) in REFERENCE]
common=[shape(p,ly).buffer(.457) for p in t.pads for ly in t.ids.values() if p.IsOnLayer(ly) and p.FlashLayer(ly)]
common += [k['shape'].buffer(.257) for k in t.keepouts if k['vias']]
common += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v) not in excluded]
common += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
common += [unary_union(references).buffer(.657)]
net=c.by_id[moving].GetNetname()
blocked=unary_union(common+[g.buffer(.457) for (u,ly),g in c.shapes.items() if u not in excluded and not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net])
xs=np.arange(42,54.001,.025);ys=np.arange(7,20.001,.025);xx,yy=np.meshgrid(xs,ys)
good=~mask(blocked,xx,yy);positions=[[round(float(x),6),round(float(y),6)] for x,y in zip(xx[good],yy[good])]
power=unary_union([c.copper.get((net,ly),GeometryCollection()) for ly in ['In2.Cu','In3.Cu']])
positions=[p for p in positions if power.buffer(-.245).contains(Point(p))]
positions.sort(key=lambda p:math.dist(p,xy(c.by_id[moving].GetPosition())))
assert positions,'No native-screened lower 3V3 transfer site'
plan['move_vias'].append(dict(uuid=moving,source_expected=via_snapshot(c.board,c.by_id[moving]),position_mm=positions[0],reason='Clear the moved INA300/supervisor group while retaining the original actual power-transfer function; native refill and all width/reference checks remain mandatory.'))
out.write_text(json.dumps(plan,indent=2)+'\n')
(b/(rev+'-preparation.json')).write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,source_solution_index=8,placement=chosen,track_checks=checks,retired_via_check=removal,eligible_transfer_sites=positions,chosen_transfer_site=positions[0],adopted=False),indent=2)+'\n')
print(json.dumps(dict(revision=rev,moved_parts=len(plan['translations']),retired_tracks=len(plan['delete_copper']),retained_considered_tracks=sum(not r['retired'] for r in checks),lower_3V3_transfer=positions[0],retired_transfer=retiring)))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
