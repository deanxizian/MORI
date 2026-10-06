"""Independent reaction-clamp assembly proposal; main files remain read-only.

Only a printed collar and its two trial fastening envelopes may change. The
horn, spline and center screw are explicitly provisional and remain untouched.
"""
from pathlib import Path
import sys, hashlib, json

HERE = Path(__file__).resolve().parent
MECHANICAL = HERE.parents[1]
OUT = HERE / 'reaction_access_candidate'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(MECHANICAL / 'scripts'))
from common import *
from validate import Solid, rigidtr
from validate_head_retention import hit
from interface_completion import axial, replace_owned
from validate_head_cleanup import geometry_record

SOURCE = MECHANICAL / 'mori_v1_2.blend'
assert Path(bpy.data.filepath).resolve() == SOURCE
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
load_collections()
for name in ('DATUMS', 'KEEP_OUT', 'DOCK', 'COUPONS'):
    COLS[name].hide_viewport = False
assembled()
bpy.context.view_layer.update()
ss = {o.name.removeprefix(PREFIX): Solid(o) for o in parts()
      if o.type == 'MESH' and o.get('group') not in ('dock', 'coupon')}
before_records = {n: geometry_record(s.o) for n, s in ss.items()}
cfg = P['belly_relayout']
rc = P['fastener_cleanup']['reaction_clamp']
tip = D['head_z'] + cfg['yaw_output_tip_from_head_mm']
seat = cfg['reaction_stem_seat_z_mm']
horn_bottom = ss['Yaw_Horn'].lo[2]


def construct(cx=7., dz=0., rear_flat=None, join_split=False):
    """Use the existing source construction to avoid guessed collar geometry."""
    collar_z = tip + 1.
    o = cyl('REACTION_REVIEW_construct', (0, 0, (seat + collar_z)/2),
            cfg['reaction_stem_radius_mm'], collar_z-seat)
    boolean(o, box('REACTION_REVIEW_D_flat', (10, 0, seat+6), (11, 20, 12)))
    union(o, cyl('REACTION_REVIEW_collar', (0, 0, tip+.5), rc['collar_outer_radius_mm'], 7))
    boolean(o, cyl('REACTION_REVIEW_horn_seat', (0, 0, horn_bottom+3), 5.2, 6))
    boolean(o, cyl('REACTION_REVIEW_cap', (0, 0, tip+5), 6.4, 5))
    boolean(o, cyl('REACTION_REVIEW_axial', (0, 0, (seat+tip+5)/2), 1.6, tip+5-seat+2))
    boolean(o, cyl('REACTION_REVIEW_spline', (0, 0, tip+2), 2.1, 8))
    boolean(o, box('REACTION_REVIEW_split', (7 if join_split else 8, 0, tip+1),
                   (14 if join_split else 12, .8, 8)))
    hy, ny = rc['screw_head_base_y_mm'], rc['nut_center_y_mm']
    boolean(o, cyl('REACTION_REVIEW_cross', (cx, 0, tip-.5+dz), 1.2, 30, 'Y'))
    boolean(o, cyl('REACTION_REVIEW_nut', (cx, (-20+ny+1.4)/2, tip-.5+dz),
                   2.75, 20+ny+1.4, 'Y', 6))
    boolean(o, cyl('REACTION_REVIEW_head', (cx, (hy+20)/2, tip-.5+dz),
                   rc['head_counterbore_radius_mm'], 20-hy, 'Y'))
    boolean(o, cyl('REACTION_REVIEW_retainer', (0, 0, cfg['reaction_retainer_z_mm']), 1.2, 20, 'Y'))
    if rear_flat is not None:
        boolean(o, box('REACTION_REVIEW_rear_trim', (0, -50-rear_flat, tip), (50, 100, 30)))
    result = Solid(o).m
    SOLIDS.pop(o.name, None)
    bpy.data.objects.remove(o, do_unlink=True)
    return result


baseline = construct()
original = ss['Yaw_Reaction_Link'].m
reconstruction_delta = max(0., (baseline-original).volume()) + max(0., (original-baseline).volume())
print('BASELINE_RECONSTRUCTION', reconstruction_delta, flush=True)
assert reconstruction_delta < .03, 'Construction does not reproduce current authoritative link'

names = ['Yaw_Reaction_Link', 'Yaw_Reaction_Clamp_Screw', 'Yaw_Reaction_Clamp_Nut']
changed = {}
cx, dz, rear_flat = 7.6, 1., 9.
changed[names[0]] = construct(cx=cx, dz=dz, rear_flat=rear_flat, join_split=True)
shift = (cx-rc['screw_x_mm'], 0., dz)
for name in names[1:]:
    changed[name] = ss[name].m.translate(shift)
geom = {n: changed.get(n, s.m) for n, s in ss.items()}

static = []
for name in names:
    for other in geom:
        if other == name or (other in names and names.index(other) < names.index(name)):
            continue
        v = hit(geom[name], geom[other], .001)
        if v:
            static.append(dict(a=name, b=other, overlap_mm3=v))
print('STATIC', len(static), static[:3], flush=True)

# Assemble the trial clamp fasteners on the detached link, not through the yoke.
bench_names = set(names) | {'Yaw_Horn'}
fastener_entries = []
for name, sign in ((names[1], 1), (names[2], -1)):
    bad = []
    for d in np.arange(0., 30.01, .25):
        m = geom[name].translate((0., sign*float(d), 0.))
        for other in bench_names - {name}:
            v = hit(m, geom[other], .001)
            if v:
                bad.append(dict(distance_mm=float(d), other=other, overlap_mm3=v))
    fastener_entries.append(dict(id=name, samples=121, hits=bad))

bolt_box = np.array(geom[names[1]].bounding_box())
tool_origin = np.array([cx, bolt_box[4]+.05, tip-.5+dz])
tool = axial(1.25, 30, tool_origin + (0, 15, 0), (0, 1, 0))
early_tool_hits = [dict(other=n, overlap_mm3=v) for n in bench_names - {names[1]}
                   if (v := hit(tool, geom[n], .001))]

# Keep the two trial fasteners and horn preinstalled during straight insertion.
entry_hits, gaps = [], []
for z in np.arange(0., 90.001, .25):
    for name in bench_names:
        moving = geom[name].translate((0., 0., float(z)))
        v = hit(moving, geom['Pitch_Yoke'], .001)
        if v:
            entry_hits.append(dict(z_mm=float(z), moving=name, overlap_mm3=v))
        else:
            gaps.append(moving.min_gap(geom['Pitch_Yoke'], 5))
print('BENCH_PATH', len(entry_hits), entry_hits[:3], min(gaps), flush=True)

# Tighten after insertion, before installing the yaw servo and pitch head.
installed_tool_hits = []
tool_fixture = bench_names | {'Pitch_Yoke'}
for other in tool_fixture - {names[1]}:
    v = hit(tool, geom[other], .001)
    if v:
        installed_tool_hits.append(dict(other=other, overlap_mm3=v))

motion_hits = []
for yaw in range(-60, 61, 10):
    for pitch in range(-20, 26, 5):
        for name, solid in ss.items():
            if solid.group not in ('yaw', 'pitch'):
                continue
            moved = geom[name].transform(np.array(rigidtr(yaw, pitch if solid.group == 'pitch' else 0))[:3, :])
            for fixed in names:
                v = hit(moved, geom[fixed], .001)
                if v:
                    motion_hits.append(dict(yaw=yaw, pitch=pitch, moving=name, fixed=fixed, overlap_mm3=v))
print('MOTION', len(motion_hits), motion_hits[:3], flush=True)

result = dict(
    revision=P['revision']+'-REACTION-C1', status='PASS', main_applied=False,
    source_blend_sha256=source_hash, blender_version=bpy.app.version_string,
    baseline_reconstruction_symmetric_difference_mm3=reconstruction_delta,
    proposed=dict(rear_flat_y_mm=-rear_flat, clamp_screw_axis_x_mm=cx,
                  clamp_screw_axis_z_mm=tip-.5+dz, fastener_translation_mm=shift,
                  split_reaches_existing_axial_bore=True, added_parts=0, changed_existing_ids=names),
    static_collisions=static, motion_poses=130, motion_collisions=motion_hits,
    detached_fastener_entry=fastener_entries, detached_tool_hits=early_tool_hits,
    preassembled_link_entry=dict(samples=361, travel_mm=90, step_mm=.25,
                                minimum_sampled_gap_mm=min(gaps), hits=entry_hits),
    tool_after_link_insertion=dict(diameter_mm=2.5, length_mm=30, hits=installed_tool_hits,
                                  status='PASS' if not installed_tool_hits else 'FAIL'),
    connected_solids=len(geom[names[0]].decompose()),
    limits=['Independent unapproved candidate; main model/config/STL untouched',
            'Existing horn, spline, lock screw and clamp fasteners remain unselected allocations',
            'Screw/nut must be preinstalled on detached link; later screw removal still requires extracting the link',
            'Finite rigid geometry samples do not qualify strength, preload, real driver or human handling',
            'Final horn size and complete harness may require further changes'])
if any((static, motion_hits, early_tool_hits, entry_hits, installed_tool_hits)) or any(x['hits'] for x in fastener_entries) or result['connected_solids'] != 1:
    result['status'] = 'FAIL'

# Save an editable inspection file only when the tested design has a viable path.
if result['status'] == 'PASS':
    for name in names:
        replace_owned(name, geom[name])
        o = ss[name].o
        o['reaction_review_candidate'] = True
        o['verification_status'] = 'PROTOTYPE_UNVALIDATED'
        o['interface_status'] = 'Independent reaction C1; not approved, final horn/fastener fit pending'
    bpy.context.view_layer.update()
    now_records = {n: geometry_record(s.o) for n, s in ss.items()}
    scope_changes = sorted(n for n in before_records if before_records[n] != now_records[n])
    assert set(scope_changes) == set(names), scope_changes
    result['actual_changed_ids'] = scope_changes
    bpy.context.scene['reaction_assembly_candidate'] = json.dumps(result['proposed'])
    bpy.context.scene['not_applied_to_main'] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'candidate.blend'))
    result['candidate_blend_sha256'] = hashlib.sha256((OUT / 'candidate.blend').read_bytes()).hexdigest()

result['source_unchanged'] = source_hash == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
assert result['source_unchanged']
(OUT / 'screening.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print('REACTION_CANDIDATE', result['status'], result['proposed'], flush=True)
