"""Compare saved main solids with the nested route study's effective inputs.

Run on the current main .blend. No study initializer is executed and no scene
or source model is saved. Historical results remain untouched.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
from common import *
from validate import Solid

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
source = Path(bpy.data.filepath).resolve()
assert source == PROJECT / 'mechanical/mori_v1_2.blend'
assert P['revision'] == 'V1.2-M1.48'
protected_paths = [source, PROJECT/'config/geometry.json',
                   PROJECT/'contracts/mechanical_interfaces.json',
                   PROJECT/'contracts/components.json']
protected = {str(p.relative_to(PROJECT)): sha(p) for p in protected_paths}
load_collections()
assembled()
bpy.context.view_layer.update()
native = {o.name.removeprefix(PREFIX): Solid(o) for o in parts()
          if o.type == 'MESH' and o.get('group') not in ['dock', 'coupon']}
assert len(native) == 209
A8 = HERE.parent / 'harness_A8'
stock = A8 / ('cam_wire_forming/lifted_end2/contact_refined_forming/'
              'root_seating/body_supply/complete_head/bridge_wire_stock')
old_path = stock/'bridge_then_shell_over_wires/diagnosis.json'
old = json.loads(old_path.read_text())
rows = []
for name in ['Yaw_Base', 'Pitch_Yoke']:
    n = native[name].m
    np.savez_compressed(HERE/f'native_{name}.npz',
                        vertices_mm=native[name].v, triangles=native[name].f)
    for variant, path in [
        ('initial_J2', A8/'terminal_threading'/f'{name}_candidate.npz'),
        ('cleaned_J2_effective_input', A8/'terminal_threading/cleaned'/f'{name}.npz'),
    ]:
        raw = np.load(path)
        c = manifold.Manifold(manifold.Mesh64(
            raw['vertices_mm'], raw['triangles'].astype(np.uint64)))
        assert c.status() == manifold.Error.NoError
        added, removed = c-n, n-c
        row = dict(part=name, candidate=variant,
                   file=str(path.relative_to(PROJECT)), sha256=sha(path),
                   native_volume_mm3=float(n.volume()), candidate_volume_mm3=float(c.volume()),
                   added_mm3=max(0., float(added.volume())),
                   removed_mm3=max(0., float(removed.volume())),
                   native_bounds_mm=list(n.bounding_box()),
                   candidate_bounds_mm=list(c.bounding_box()))
        if name == 'Yaw_Base':
            slices = []
            for z, polygons in old['sections'][name].items():
                historical = manifold.CrossSection([np.asarray(q) for q in polygons])
                ns, cs = n.slice(float(z)), c.slice(float(z))
                difference = lambda a, b: float((a-b).area()+(b-a).area())
                slices.append(dict(z_mm=float(z), historical_area_mm2=float(historical.area()),
                                   historical_vs_native_symmetric_area_mm2=difference(historical, ns),
                                   historical_vs_candidate_symmetric_area_mm2=difference(historical, cs)))
            row['historical_section_comparisons'] = slices
        rows.append(row)

# Directly repeat the recorded local first-contact witness using the native
# bridge. These coordinates are a preserved padded-terminal allocation.
temporary = np.load(stock/'bridge_then_shell_over_wires/temporary_wires.npz')
report = dict(
    status='PASS', scope='Geometry provenance audit, not a harness-fit pass',
    revision=P['revision'], source_main_sha256=protected[str(source.relative_to(PROJECT))],
    protected_sources=protected, script_sha256=sha(__file__),
    historical_diagnostic=str(old_path.relative_to(PROJECT)), historical_diagnostic_sha256=sha(old_path),
    native_parts=len(native), comparisons=rows,
    initialization_chain=[
        'screen_bridge_then_shell_over_wires.py', 'screen_CAM_PH_attached_wire_entry.py',
        'screen_CAM_PH_shell16_stepped_entry.py', 'screen_CAM_PH_shell16_deferred_waypoints.py',
        'plan_CAM_PH_shell16_deferred_entry.py', 'plan_CAM_PH_rotated_entry_fast.py',
        'plan_CAM_PH_rotated_entry.py', 'screen_CAM_bridge_wire_stock.py',
        'plan_h06_documented_mates.py', 'plan_h06_body_leads.py',
    ],
    replacement_sites=[dict(file='plan_h06_body_leads.py', action='replace_owned from terminal_threading/*_candidate.npz'),
                       dict(file='plan_h06_documented_mates.py', action='replace ss and object mesh from terminal_threading/cleaned/*.npz')],
    historical_original_solids_claim='FAIL',
    actual_historical_geometry='Unadopted cleaned J2 candidates, not native Yaw_Base/Pitch_Yoke',
    consequences=[
        'Historical native-bridge label and substituted_prints=[] are invalid.',
        'Historical candidate results are preserved; no complete native-harness pass follows from them.',
        'Local collision witnesses must be rechecked on current native solids before reuse.',
    ],
    cached_temporary_wire_keys=list(temporary.keys()),
    main_model_applied=False, manufacturing_release=False,
)
report['initializer_sources'] = {
    p:sha(A8/p) for p in report['initialization_chain']}
for row in rows:
    if row['candidate']=='cleaned_J2_effective_input' and row['part']=='Yaw_Base':
        assert row['added_mm3']+row['removed_mm3'] > 1.
        assert max(s['historical_vs_candidate_symmetric_area_mm2'] for s in row['historical_section_comparisons']) < 1e-4
        assert max(s['historical_vs_native_symmetric_area_mm2'] for s in row['historical_section_comparisons']) > 1.
assert all(sha(PROJECT/p)==h for p,h in protected.items())
report['protected_sources_unchanged'] = True
(HERE/'source_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('NATIVE_SOURCE_AUDIT', [(r['part'],r['candidate'],r['added_mm3'],r['removed_mm3']) for r in rows], flush=True)
print('HISTORICAL_NATIVE_CLAIM', report['historical_original_solids_claim'], flush=True)
