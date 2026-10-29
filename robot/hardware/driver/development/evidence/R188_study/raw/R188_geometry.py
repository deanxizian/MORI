"""Read-only native geometry review of reference-repair copper and transfer moves.

Projected areas are nominal CAD comparisons, not capacitance, temperature,
measured crosstalk or physical qualification. Report added metal separately
from old metal recreated with new track UUIDs.
"""
import ast,collections,hashlib,json,sys
from pathlib import Path
from shapely.ops import polygonize
from shapely.geometry import box
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-geometry-review.json');assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/rev/'MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/(rev+'-plan.json')).read_text());assert a.sha==plan['board_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'frozen_fab','exec'))
stack=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
def shield(first,last):
    lo,hi=sorted([stack.index(first),stack.index(last)])
    layers=[l for l in stack[lo+1:hi] if l in ['In1.Cu','In4.Cu']]
    return layers,unary_union([c.reference_ground_fills[l] for l in layers])
new=[t for t in c.segments if uid(t) not in a.by_id];grouped=collections.defaultdict(list)
for t in new:grouped[t.GetNetname(),c.board.GetLayerName(t.GetLayer())].append(t)
same=[];body_rows=[];foreign_rows=[];lengths=[]
for (net,layer),tracks in grouped.items():
    stroke=unary_union([c.shapes[uid(t),layer] for t in tracks])
    old=unary_union([a.shapes[uid(t),layer] for t in a.segments if t.GetNetname()==net and a.board.GetLayerName(t.GetLayer())==layer])
    added=stroke.difference(old)
    own_lands=unary_union([s for (u,l),s in c.shapes.items() if l==layer and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
    for f in c.footprints:
        face=c.board.GetLayerName(f.GetLayer());body=fab(f)
        hit=stroke.difference(own_lands).intersection(body)
        if hit.area<=1e-8:continue
        if face==layer:same.append(dict(net=net,layer=layer,reference=f.GetReference(),area_mm2=hit.area));continue
        refs,g=shield(layer,face);new_hit=added.intersection(body)
        body_rows.append(dict(net=net,layer=layer,reference=f.GetReference(),component_face=face,
            overlap_mm2=hit.area,added_overlap_mm2=new_hit.area,intervening_ground_layers=refs,
            unshielded_added_mm2=new_hit.difference(g).area))
    for other_layer in ['F.Cu','In2.Cu','In3.Cu','B.Cu']:
        if other_layer==layer:continue
        refs,g=shield(layer,other_layer)
        for other in sorted({n for n,ly in c.copper if ly==other_layer}):
            if other in [net,'GND','']:continue
            hit=stroke.intersection(c.copper[other,other_layer]);new_hit=added.intersection(c.copper[other,other_layer])
            if hit.area>1e-8:
                foreign_rows.append(dict(net=net,layer=layer,other_net=other,other_layer=other_layer,
                    overlap_mm2=hit.area,added_overlap_mm2=new_hit.area,intervening_ground_layers=refs,
                    unshielded_added_mm2=new_hit.difference(g).area))
    retired=[a.by_id[u] for u in plan['delete_copper'] if a.by_id[u].GetNetname()==net and a.board.GetLayerName(a.by_id[u].GetLayer())==layer]
    lengths.append(dict(net=net,layer=layer,source_replaced_length_mm=sum(t.GetLength()/1e6 for t in retired),
        candidate_length_mm=sum(t.GetLength()/1e6 for t in tracks),added_metal_mm2=added.area))
moved={r['uuid'] for key in ['move_vias','move_ground_vias'] for r in plan.get(key,[])}
unchanged=[v for v in a.vias if uid(v) not in moved]
assert len(c.vias)==len(a.vias)==324
assert all(via_snapshot(a.board,v)==via_snapshot(c.board,c.by_id[uid(v)]) for v in unchanged)
ground=[v for v in a.vias if v.GetNetname()=='GND'];assert len(ground)==114
assert all(via_snapshot(a.board,v)==via_snapshot(c.board,c.by_id[uid(v)]) for v in ground if uid(v) not in moved)
assert all(c.ground_reference_contacts(c.by_id[r['uuid']])[layer]>1e-8 for r in plan.get('move_ground_vias',[]) for layer in ['In1.Cu','In4.Cu'])
transfer_reviews=[]
for spec in plan.get('move_vias',[]) + plan.get('move_ground_vias',[]):
    v=c.by_id[spec['uuid']]
    ref_contacts=c.ground_reference_anchors
    nearest=sorted((Point(xy(v.GetPosition())).distance(Point(xy(g.GetPosition()))),uid(g)) for g in ref_contacts if uid(g)!=uid(v))
    transfer_reviews.append(dict(uuid=uid(v),source=spec['source_expected'],candidate=via_snapshot(c.board,v),
        nearest_actual_ground_anchor_mm=nearest[0][0],ground_anchor_uuid=nearest[0][1]))
result=dict(scope=__doc__,source_sha256=a.sha,candidate_sha256=c.sha,track_counts=dict(before=len(a.segments),after=len(c.segments)),
    via_counts=dict(before=len(a.vias),after=len(c.vias)),footprint_count=len(c.footprints),
    retained_vias_unchanged=len(unchanged),moved_non_GND_vias=len(plan.get('move_vias',[])),moved_GND_vias=len(plan.get('move_ground_vias',[])),original_ground_via_identities_preserved=len(ground),original_ground_vias_unchanged=sum(uid(v) not in moved for v in ground),
    new_holes=0,moved_ground_fill_contacts={r['uuid']:c.ground_reference_contacts(c.by_id[r['uuid']]) for r in plan.get('move_ground_vias',[])},net_layer_lengths=lengths,same_face_nominal_body_hits=same,body_projections=body_rows,
    foreign_copper_projections=foreign_rows,moved_transfer_review=transfer_reviews,
    physical='NOT_TESTED',full_noise_transient_thermal='NOT_TESTED',manufacturing_release=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(counts=result['track_counts'],same_face_hits=len(same),body_projections=len(body_rows),
    unshielded_added_body=[r for r in body_rows if r['unshielded_added_mm2']>1e-8],
    unshielded_added_copper=[r for r in foreign_rows if r['unshielded_added_mm2']>1e-8],lengths=lengths),indent=2))
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
