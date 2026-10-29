"""Prepare one complete eight-part native layout with minimum transfer changes.

Preserves supply and unchanged bypass source branches where exact new native
geometry permits them. Only the actually colliding lower 3V3 via relocates;
the CT transfer retires after all old leads are explicitly replaced. Placement
screening is not electrical acceptance; full refill and audits follow.
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
b=Path('robot/.state/c3-completion/trials');out=b/'R174A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
t=Copper(c.path);fps={f.GetReference():f for f in t.footprints}
screen=json.loads((b/'R174-ranked-placement.json').read_text());assert screen['source_sha256']==c.sha
chosen=screen['solutions'][0]
assert chosen['actually_intersected_transfer_sites']==['c89d9b75-62b7-4bdc-8fe8-09516366b58c']
plan=dict(revision='R174A',scope=__doc__,board_sha256=c.sha,translations=[],delete_copper=sorted(set(screen['prospectively_retired_tracks'])|set(chosen['additional_track_dependencies'])),deleted_copper_expected={},move_vias=[],remove_obsolete_vias=[],vias=[],routes=[])
for row in chosen['parts']:
 ref=row['reference'];f=fps[ref];old=list(xy(f.GetPosition()));angle=f.GetOrientationDegrees();face=t.board.GetLayerName(f.GetLayer());new=row['position_mm'];a=row['rotation_deg'];delta=[round(new[i]-old[i],6) for i in range(2)]
 if old==new and int(angle)%360==a and face==row['face']:continue
 spec=dict(reference=ref,from_mm=old,delta_mm=delta,rotation_deg=a)
 owned=[z for z in t.zones if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_'+ref+'_')]
 reconstruct=any('_VIA_' in z.GetZoneName() for z in owned)
 if reconstruct:spec.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True,repartition_fixed_via_guards=True)
 if face!=row['face']:
  assert ref.startswith('R') and not reconstruct
  spec['side_change']=dict(from_face=face,to_face=row['face'],from_rotation_deg=angle,axis='LEFT_RIGHT',reason='Complete INA300/supervisor group placement preserves values, actual pad geometry and pin/net mapping.')
  f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);flipped=f.GetOrientationDegrees()
  for z in owned:
   g=translate(rotate(scale(polyset(z.Outline()),xfact=-1,yfact=1,origin=old),-(a-flipped),origin=old),xoff=delta[0],yoff=delta[1]);set_outline(z,g);z.SetLayer(t.board.GetLayerID(row['face']))
 else:move_body_guards(owned,delta,reconstruct,a-angle,old,reconstruct,reconstruct)
 f.SetOrientationDegrees(a);f.Move(point_mm(delta));plan['translations'].append(spec)
 for p in f.Pads():assert list(xy(p.GetPosition()))==row['pads'][p.GetNumber()]['position_mm']

node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
# These source branches remain useful and do not terminate on a moved pad.
keep=['44e785d8-303e-5e78-b5ba-3d13086b7fe0','3b2b6f74-d6fb-56a8-94bc-4488965c482b','bc3e9793-b9cd-54b1-b44c-64b91f6e9a06','65bcfb8b-ccb8-414b-9655-86c9c7b51068','faea7b4d-249a-47b7-8402-16bf75873e0c','dcb2b41a-82bd-47f9-9a25-09dbdf14ff28','7c457b1b-8640-4205-8467-6ef9cfeae45d','1d4ee9c6-471f-4c4a-bbb3-a128d5d11e6d']
kept=[]
for u in keep:
 assert u in plan['delete_copper'];track=c.by_id[u];ly=c.board.GetLayerName(track.GetLayer());s=c.shapes[u,ly];net=track.GetNetname()
 assert not any(s.distance(shape(p,t.ids[ly]))<.1999996-1e-9 for p in t.pads if p.IsOnLayer(t.ids[ly]) and p.GetNetname()!=net),u
 assert not any(s.intersection(k['shape']).area>1e-8 for k in t.keepouts if k['tracks'] and ly in k['layers']),u
 for f in t.footprints:
  if f.GetLayer()!=t.ids[ly]:continue
  body=fab(f).difference(unary_union([shape(p,t.ids[ly]) for p in f.Pads()]));assert s.intersection(body).area<1e-8,(u,f.GetReference())
 plan['delete_copper'].remove(u);kept.append(u)
for u in plan['delete_copper']:
 tt=c.by_id[u];plan['deleted_copper_expected'][u]=dict(net=tt.GetNetname(),layer=c.board.GetLayerName(tt.GetLayer()),width_mm=tt.GetWidth()/1e6,start_mm=list(xy(tt.GetStart())),end_mm=list(xy(tt.GetEnd())))
v=c.by_id['703768b9-e4a4-4421-98a3-394d066ff7e6']
plan['remove_obsolete_vias']=[dict(uuid=uid(v),source_expected=via_snapshot(c.board,v),remaining_contact_layers=[],reason='The original CT leads are explicitly replaced; both CT terminal parts now occupy B.Cu. This retired via has no remaining source copper contacts.')]
mov='c89d9b75-62b7-4bdc-8fe8-09516366b58c';excluded=set(plan['delete_copper'])|{mov,uid(v)}
references=[c.shapes[uid(tt),c.board.GetLayerName(tt.GetLayer())].intersection(c.copper.get(('GND',REFERENCE[c.board.GetLayerName(tt.GetLayer())]),GeometryCollection())) for tt in c.segments if uid(tt) not in excluded and tt.GetNetname()!='GND' and c.board.GetLayerName(tt.GetLayer()) in REFERENCE]
common=[shape(p,ly).buffer(.457) for p in t.pads for ly in t.ids.values() if p.IsOnLayer(ly) and p.FlashLayer(ly)]
common += [k['shape'].buffer(.257) for k in t.keepouts if k['vias']]
common += [Point(xy(vv.GetPosition())).buffer(vv.GetDrillValue()/2e6+.307) for vv in c.vias if uid(vv) not in excluded]
common += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
common += [unary_union(references).buffer(.657)]
net=c.by_id[mov].GetNetname();blocked=unary_union(common+[s.buffer(.457) for (u,ly),s in c.shapes.items() if u not in excluded and not isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net])
xs=np.arange(42,54.001,.05);ys=np.arange(7,19.001,.05);xx,yy=np.meshgrid(xs,ys)
good=~mask(blocked,xx,yy);positions=[[round(float(x),6),round(float(y),6)] for x,y in zip(xx[good],yy[good])]
existing_power=unary_union([c.copper.get((net,ly),GeometryCollection()) for ly in ['In2.Cu','In3.Cu']])
positions=[p for p in positions if existing_power.buffer(-.245).contains(Point(p))]
positions.sort(key=lambda p:math.dist(p,xy(c.by_id[mov].GetPosition())))
assert positions,'No screened 3V3 transfer site'
plan['move_vias'].append(dict(uuid=mov,source_expected=via_snapshot(c.board,c.by_id[mov]),position_mm=positions[0],reason='Original lower 3V3 via conflicts with relocated FAULT pad. New position screens all native pads, tracks, body guards and retained reference copper; refill and original power widths remain mandatory.'))
out.write_text(json.dumps(plan,indent=2)+'\n')
(b/'R174A-preparation-screen.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,placement=chosen,preserved_source_branches=kept,eligible_transfer_sites=positions,chosen_transfer_site=positions[0],adopted=False),indent=2)+'\n')
print(json.dumps(dict(plan=str(out),moved_parts=len(plan['translations']),retired_tracks=len(plan['delete_copper']),kept_source_branches=len(kept),transfer=positions[0],eligible_sites=len(positions))))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
