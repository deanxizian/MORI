"""Native local geometry, return and adjacent-layer projection review for R185I.

Distances/areas are nominal CAD values, not physical, EMC or thermal results.
In2 and In3 are adjacent copper layers; no intervening-ground claim is made.
"""
import ast,hashlib,json,math,sys
from pathlib import Path
from shapely.ops import polygonize
from shapely.geometry import box
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185I-geometry-review.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(str(b/'R185I/MORI_Interface_C3.kicad_pcb'))
plan=json.loads((b/'R185I-plan.json').read_text());reg=json.loads((b/'R185I-checks/regression.json').read_text())
assert a.sha==plan['board_sha256'] and c.sha==reg['board_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
new=[t for t in c.segments if uid(t) not in a.by_id];newvias=[v for v in c.vias if uid(v) not in a.by_id]
assert len(new)==5 and len(newvias)==1
ground_uuid=plan['move_ground_vias'][0]['uuid'];gv=c.by_id[ground_uuid]
old_gnd=[v for v in a.vias if v.GetNetname()=='GND'];assert len(old_gnd)==114
assert all(uid(v) in c.by_id and c.by_id[uid(v)].GetNetname()=='GND' for v in old_gnd)
unchanged=[v for v in a.vias if uid(v)!=ground_uuid]
assert len(unchanged)==323 and all(via_snapshot(a.board,v)==via_snapshot(c.board,c.by_id[uid(v)]) for v in unchanged)
groups={}
for t in new:
    ly=c.board.GetLayerName(t.GetLayer());groups.setdefault((t.GetNetname(),ly),[]).append(t)
route_rows=[];same_face=[]
for (net,ly),tracks in groups.items():
    stroke=unary_union([c.shapes[uid(t),ly] for t in tracks]);bodies=[];projections=[];near=[]
    ownpads=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
    for f in c.footprints:
        face=c.board.GetLayerName(f.GetLayer());hit=stroke.difference(ownpads).intersection(fab(f))
        if hit.area<=1e-8:continue
        intervening=([REFERENCE[ly]] if ly in ['F.Cu','B.Cu'] and face!=ly else
                     ['In1.Cu'] if ly=='In2.Cu' and face=='F.Cu' else
                     ['In4.Cu'] if ly=='In2.Cu' and face=='B.Cu' else [])
        entry=dict(component=f.GetReference(),face=face,overlap_mm2=hit.area,intervening_ground_layers=intervening,
                   uncovered_by_intervening_ground_mm2=hit.difference(unary_union([c.copper['GND',r] for r in intervening])).area if intervening else hit.area)
        bodies.append(entry)
        if face==ly:same_face.append(entry)
    for other_layer in LAYERS:
        if other_layer==ly:continue
        for (other_net,l),shape_ in c.copper.items():
            if l!=other_layer or other_net in [net,'GND','']:continue
            hit=stroke.intersection(shape_)
            if hit.area<=1e-8:continue
            indices=sorted([LAYERS.index(ly),LAYERS.index(other_layer)])
            between=[r for r in ['In1.Cu','In4.Cu'] if indices[0]<LAYERS.index(r)<indices[1]]
            new_projection=hit.difference(a.copper.get((net,ly),GeometryCollection()))
            projections.append(dict(net=other_net,layer=other_layer,overlap_mm2=hit.area,new_projection_mm2=new_projection.area,
                                    intervening_ground_layers=between,
                                    uncovered_by_intervening_ground_mm2=hit.difference(unary_union([c.copper['GND',r] for r in between])).area if between else hit.area))
    for (u,l),s in c.shapes.items():
        o=c.by_id[u]
        if l!=ly or o.GetNetname() in [net,'']:continue
        distance=stroke.distance(s)
        if distance<.8:near.append(dict(uuid=u,net=o.GetNetname(),kind=type(o).__name__,copper_edge_distance_mm=distance))
    route_rows.append(dict(net=net,layer=ly,segment_count=len(tracks),length_mm=sum(t.GetLength()/1e6 for t in tracks),
                           body_projections=bodies,foreign_layer_copper_projections=projections,nearest_same_layer=sorted(near,key=lambda r:r['copper_edge_distance_mm'])))
special={ground_uuid,uid(newvias[0]),'0a9dc1d8-9c18-4afe-a8ce-01042c59ca4d','2ceba827-433b-44de-af01-ce89cb121093','8a98772c-3e00-471a-9f47-92d69936d1fe'}
transitions=[r for r in reg['reference_transitions'] if r['uuid'] in special]
contacts={ly:dict(land_contact_area_mm2=c.shapes[ground_uuid,ly].intersection(c.copper['GND',ly]).area,
                  plane_component_count=len(parts(c.copper['GND',ly]))) for ly in ['In1.Cu','In4.Cu']}
assert all(r['land_contact_area_mm2']>0 for r in contacts.values())
result=dict(scope=__doc__,source_sha256=a.sha,candidate_sha256=c.sha,track_counts=dict(before=len(a.segments),after=len(c.segments)),
            via_counts=dict(before=len(a.vias),after=len(c.vias)),unchanged_source_vias=323,original_GND_via_identities_preserved=114,
            moved_GND=dict(uuid=ground_uuid,before=via_snapshot(a.board,a.by_id[ground_uuid]),after=via_snapshot(c.board,gv),actual_plane_contacts=contacts),
            new_via=via_snapshot(c.board,newvias[0]),same_face_nominal_body_hits=same_face,routes=route_rows,transition_reviews=transitions,
            source_connection_losses=reg['lost_pad_connections'],old_reference_losses=reg['retained_trace_reference_loss'],
            power_checks_pass=sum(r['status']=='PASS' for r in reg['power_width']),critical_adjacency_pass=sum(r['status']=='PASS' for r in reg['critical_placement']),
            caution='In2 supply and In3 HEAD_OE have an adjacent-layer projection without an intervening ground plane. Their own reference planes remain continuous in the recorded screen. No transient coupling, false-enable immunity, thermal or EMC qualification is inferred.',
            manufacturer_layout_qualification='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['track_counts','via_counts','same_face_nominal_body_hits','transition_reviews']},indent=2))
for r in route_rows:print(json.dumps(dict(net=r['net'],length=r['length_mm'],unshielded_projections=[p for p in r['foreign_layer_copper_projections'] if p['uncovered_by_intervening_ground_mm2']>1e-8],nearest=r['nearest_same_layer'][:3]),indent=2))
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha and hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
