"""Actual-board save/readback and refusal checks for explicit guard repartition."""
import json,sys
from pathlib import Path
from shapely.affinity import rotate
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_settings
from build_trial import move_body_guards
b=Path('robot/.state/c3-completion/trials');out=b/'R169-guard-repartition-checks.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');q=Copper(b/'R169B/MORI_Interface_C3.kicad_pcb');assert a.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
az={uid(z):z for z in a.zones};bz={uid(z):z for z in q.zones};owned=[z for z in a.zones if z.GetZoneName().startswith('BODY_U1701_')];ids={uid(z) for z in owned};body=unary_union([polyset(z.Outline()) for z in owned if z.GetDoNotAllowTracks()]);old_via=unary_union([polyset(z.Outline()) for z in owned if z.GetDoNotAllowVias()]);fixed=body.difference(old_via);expected=rotate(body,-180,origin=(47.25,12.35)).difference(fixed);actual=unary_union([polyset(bz[uid(z)].Outline()) for z in owned if z.GetDoNotAllowVias()])
checks={
 'same_native_zone_ids':set(az)==set(bz),
 'all_native_zone_settings_unchanged':all(zone_settings(a.board,z)==zone_settings(q.board,bz[i]) for i,z in az.items()),
 'unowned_native_outlines_unchanged':all(polyset(z.Outline()).symmetric_difference(polyset(bz[i].Outline())).area<1e-8 for i,z in az.items() if i not in ids),
 'rotated_track_guards_exact':all(rotate(polyset(z.Outline()),-180,origin=(47.25,12.35)).symmetric_difference(polyset(bz[uid(z)].Outline())).area<1e-8 for z in owned if z.GetDoNotAllowTracks()),
 'via_union_exact_after_native_save_refill':actual.symmetric_difference(expected).area<1e-8,
 'fixed_source_cutouts_not_filled':actual.intersection(fixed).area<1e-8,
 'each_native_via_guard_contiguous':all(len(parts(polyset(bz[uid(z)].Outline())))==1 for z in owned if z.GetDoNotAllowVias()),
 'all_114_source_ground_vias_exact':len([v for v in a.vias if v.GetNetname()=='GND'])==114 and all(via_snapshot(a.board,v)==via_snapshot(q.board,q.by_id[uid(v)]) for v in a.vias if v.GetNetname()=='GND'),
}
refusals=[]
for name,mutation,args in [
 ('no_explicit_repartition',None,dict(reconstruct=True,rotate_fixed_cutouts=True)),
 ('mixed_native_guard_rules','mixed',dict(reconstruct=True,rotate_fixed_cutouts=True,repartition_fixed_cutouts=True)),
 ('repartition_without_reconstruction',None,dict(reconstruct=False,repartition_fixed_cutouts=True)),
]:
 c=Copper(a.path);zs=[z for z in c.zones if z.GetZoneName().startswith('BODY_U1701_')]
 if mutation=='mixed':next(z for z in zs if z.GetDoNotAllowVias()).SetDoNotAllowPads(True)
 try:
  move_body_guards(zs,[0,0],rotation_delta=180,origin_mm=(47.25,12.35),**args)
 except ValueError as e:
  refusals.append(dict(case=name,error=str(e)));checks[name+'_refused']=True
 else:checks[name+'_refused']=False
checks['canonical_bytes_unchanged']=hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha
result=dict(scope=__doc__,source_sha256=a.sha,comparison_sha256=q.sha,status='PASS' if all(checks.values()) else 'FAIL',checks=checks,refusals=refusals,original_via_guard_count=sum(z.GetDoNotAllowVias() for z in owned),target_union_area_mm2=expected.area,native_union_difference_mm2=actual.symmetric_difference(expected).area,complete_board_qualification=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert all(checks.values())
