"""J3M: open the existing upper channel roofs in an independent candidate.

The cutter is derived from the material already removed for J3's upper wire
passage, then swept upward to the same top surface. It connects the mouth to
the inner cavity without moving a seat, adding a part, or inventing a new hole.
"""
from pathlib import Path
MOUTH_BUILD_SCRIPT=Path(__file__).resolve();MOUTH_BUILD_DIR=MOUTH_BUILD_SCRIPT.parent
MOUTH_BUILD_HELPER=MOUTH_BUILD_DIR/'plan_h06_documented_mates.py';__file__=str(MOUTH_BUILD_HELPER)
exec(compile(MOUTH_BUILD_HELPER.read_text().split('\nports=json.loads',1)[0],str(MOUTH_BUILD_HELPER),'exec'),globals())
__file__=str(MOUTH_BUILD_SCRIPT)
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record
J3=MOUTH_BUILD_DIR/'assembly_feed_v3';OUT=J3/'open_mouth';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before_records={n:geometry_record(s.o) for n,s in ss.items()}
def from_npz(path):
    z=np.load(path);return manifold.Manifold(manifold.Mesh64(vert_properties=z['vertices_mm'],tri_verts=z['triangles'].astype(np.uint64)))
def cache(path,m):
    mm=m.to_mesh64();np.savez_compressed(path,vertices_mm=np.array(mm.vert_properties[:,:3]),triangles=np.array(mm.tri_verts))
original={n:from_npz(J3/'cleaned'/f'{n}.npz') for n in ['Yaw_Base','Pitch_Yoke']}
main_yoke=from_npz(MOUTH_BUILD_DIR/'joined_entry_candidate/Pitch_Yoke_baseline.npz')
# This box only limits the upper mouth, not the final cutter's profile.
# Coordinates: radial12.5..19, tangential+-1.2, Z183.5..191.01. The source
# top surface is Z191; functional journal/bearing surfaces are far below.
local_limit=manifold.Manifold.cube([6.5,2.4,7.51]).translate([12.5,-1.2,183.5])
regions=[];cutters=[];cuts=[]
for phase in [45,135,225,315]:
    region=local_limit.rotate((0,0,phase));regions.append(region)
    removed=(main_yoke-original['Pitch_Yoke'])^region
    assert removed.volume()>0
    # Convex vertical opening of an already existing passage. The lower
    # boundary stays at/below that passage; the new cut removes its roof.
    tool=manifold.Manifold.batch_hull([removed,removed.translate((0,0,8.))])^region
    actual=original['Pitch_Yoke']^tool
    cuts.append({'phase_deg':phase,'existing_cut_volume_mm3':float(removed.volume()),
        'roof_removal_volume_mm3':float(actual.volume()),'removed_bounds_mm':list(actual.bounding_box())})
    cache(OUT/f'mouth_cut_{phase}.npz',tool);cutters.append(tool)
all_tools=manifold.Manifold.batch_boolean(cutters,manifold.OpType.Add)
allowed=manifold.Manifold.batch_boolean(regions,manifold.OpType.Add)
candidate=original['Pitch_Yoke']-all_tools;delta=original['Pitch_Yoke']-candidate
assert (candidate-original['Pitch_Yoke']).volume()<1e-7
assert (delta-allowed).volume()<1e-7
parts=[p for p in candidate.decompose() if abs(p.volume())>1e-7]
assert len(parts)==1
candidate=parts[0]
# Measure the actual removed material against all unmodified parts. Distances
# to fixed parts concern this zero-pose feature only; complete motion belongs
# to the inherited/reloaded checks and the no-addition proof.
gaps=[]
for name,s in ss.items():
    if name in original:continue
    g=float(delta.min_gap(s.m,4.))
    if g<4:gaps.append({'source_part':name,'minimum_gap_mm':g})
assert all(r['minimum_gap_mm']>.3 for r in gaps),gaps
cache(OUT/'Pitch_Yoke_roof_removed.npz',delta)
cache(OUT/'Pitch_Yoke_before_mouth.npz',original['Pitch_Yoke'])
for name,m in [('Yaw_Base',original['Yaw_Base']),('Pitch_Yoke',candidate)]:
    obj=ss[name].o;replace_owned(name,m);ss[name]=Solid(obj)
    cache(OUT/f'{name}_candidate.npz',m)
changes=sorted(n for n,s in ss.items() if geometry_record(s.o)!=before_records[n])
assert changes==['Pitch_Yoke','Yaw_Base']
bpy.context.scene['independent_unapproved_study']='J3M: existing upper feed passage opened upward; no main adoption'
bpy.context.scene['main_model_not_updated']=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))

# Frozen input snapshot for the same analytic feed and replay code. Previous
# results are referenced by hash, not copied and relabeled as a new PASS.
(OUT/'coupled_feed_screen.json').write_bytes((J3/'coupled_feed_screen.json').read_bytes())
construction=json.loads((J3/'candidate_screen.json').read_text())
construction.update(scope='J3M upper mouth subtraction from J3; unchanged feed construction inherited and referenced, reload checks pending',
    source_script_sha256=sha(MOUTH_BUILD_SCRIPT),source_J3_construction_sha256=sha(J3/'candidate_screen.json'),
    source_J3_cleaned_candidate_sha256=sha(J3/'cleaned/candidate.blend'),candidate_blend_sha256=sha(OUT/'candidate.blend'),
    parts=[{'part':n,'volume_mm3':float(m.volume())} for n,m in [('Yaw_Base',original['Yaw_Base']),('Pitch_Yoke',candidate)]],
    source_J3_original_parts={n:sha(J3/'cleaned'/f'{n}.npz') for n in original},
    upper_mouth={'status':'PASS','scope':'Exact-kernel subtraction, locality, connectivity and zero-pose source gaps only',
        'cutter_definition':'Convex vertical sweep of existing removed passage material, restricted to documented mouth region',
        'region_local_rtz_mm':[[12.5,-1.2,183.5],[19.,1.2,191.01]],'cuts':cuts,
        'removed_volume_mm3':float(delta.volume()),'added_volume_mm3':float((candidate-original['Pitch_Yoke']).volume()),
        'outside_region_removed_mm3':float((delta-allowed).volume()),'source_gaps_below_4mm':gaps,
        'whole_part_components':1,'all_fine_edges':'NOT_TESTED','physical_strength':'NOT_TESTED'},
    installed_routing_replay='NOT_TESTED',raw_storage_reload='NOT_TESTED',main_model_applied=False,
    complete_harness='BLOCKED',manufacturing_release=False)
(OUT/'candidate_screen.json').write_text(json.dumps(construction,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('OPEN_MOUTH_CONSTRUCTION',construction['upper_mouth'],flush=True)
