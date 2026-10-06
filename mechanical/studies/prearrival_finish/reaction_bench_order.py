"""Unmodified-main bench-order alternatives: bare link, delayed hardware, free yaw.

Nothing is saved to the model. The body, servos and bearings are absent at this
bench stage. A free final pose is not treated as an insertion path.
"""
from pathlib import Path
import sys, json, hashlib, math, time
HERE = Path(__file__).resolve().parent
M = HERE.parents[1]
sys.path.insert(0, str(M / 'scripts'))
from common import *
from validate import Solid
from validate_head_retention import hit
from interface_completion import axial

load_collections()
for n in ['DATUMS', 'KEEP_OUT', 'DOCK', 'COUPONS']:
    COLS[n].hide_viewport = False
assembled(); bpy.context.view_layer.update()
source = Path(bpy.data.filepath)
before = hashlib.sha256(source.read_bytes()).hexdigest()
ss = {o.name.removeprefix(PREFIX): Solid(o) for o in parts()
      if o.get('group') not in ['dock', 'coupon']}
fixture = ss['Pitch_Yoke'].m
names = ['Yaw_Reaction_Link', 'Yaw_Reaction_Clamp_Screw', 'Yaw_Reaction_Clamp_Nut', 'Yaw_Horn']
bare = ss[names[0]].m
preassembled = manifold.Manifold()
for n in names:
    preassembled += ss[n].m
bolt = ss['Yaw_Reaction_Clamp_Screw']; center = (bolt.lo + bolt.hi) / 2
tool_start = np.array([center[0], bolt.hi[1] + .05, center[2]])
tool = axial(1.25, 30, tool_start + [0, 15, 0], [0, 1, 0])

def yaw_matrix(deg):
    return np.array(Matrix.Rotation(math.radians(deg), 4, 'Z'))[:3, :]

rows = []
for angle in range(0, 360, 2):
    tr = yaw_matrix(angle)
    b = bare.transform(tr); combined = preassembled.transform(tr)
    rows.append(dict(yaw_deg=angle,
        bare_overlap_mm3=hit(b, fixture, .001), bare_gap_mm=b.min_gap(fixture, 2),
        assembled_overlap_mm3=hit(combined, fixture, .001),
        assembled_gap_mm=combined.min_gap(fixture, 2),
        tool_overlap_mm3=hit(tool.transform(tr), fixture, .001)))

# Is there a hardware-entry/tool orientation on the isolated yoke that can
# rotate back to the nominal orientation? This is separate from initial entry.
order_rows = []
for angle in range(-180, 181, 10):
    yaw_path = []
    for a in np.linspace(0, angle, int(abs(angle)) + 1):
        m = preassembled.transform(yaw_matrix(float(a)))
        v = hit(m, fixture, .001)
        if v:
            yaw_path.append(dict(yaw_deg=float(a), overlap_mm3=v)); break
    if yaw_path:
        order_rows.append(dict(yaw_deg=angle, status='FAIL', blocked_phase='rotate_to_nominal', hit=yaw_path[0]))
        continue
    tr = yaw_matrix(angle)
    direction = np.array(Matrix.Rotation(math.radians(angle), 3, 'Z')) @ np.array([0, 1, 0])
    blocked = []
    fixed_link = bare.transform(tr)
    for name, sign in [(names[1], 1), (names[2], -1)]:
        for d in np.arange(0, 30.01, .25):
            moving = ss[name].m.transform(tr).translate(sign * direction * float(d))
            for target, f in [('Pitch_Yoke', fixture), ('Yaw_Reaction_Link', fixed_link)]:
                v = hit(moving, f, .001)
                if v:
                    blocked.append(dict(name=name, distance_mm=float(d), target=target, overlap_mm3=v)); break
            if blocked: break
        if blocked: break
    vt = hit(tool.transform(tr), fixture, .001)
    order_rows.append(dict(yaw_deg=angle, status='PASS' if not blocked and not vt else 'FAIL',
                           entry_hits=blocked, tool_overlap_mm3=vt))

out = dict(revision=P['revision'], source_blend_sha256=before,
    status='BLOCKED', main_applied=False, source_unchanged=before == hashlib.sha256(source.read_bytes()).hexdigest(),
    bare_initial_gap_mm=bare.min_gap(fixture, 5),
    preassembled_initial_gap_mm=preassembled.min_gap(fixture, 5),
    yaw_sampling_deg=2, orientation_checks=rows, bench_fastener_orders=order_rows,
    usable_delayed_fastening_angles_deg=[r['yaw_deg'] for r in order_rows if r['status'] == 'PASS'],
    scope='Bare detached yoke before bearings, body, servos and head; delayed clamp hardware and free relative yaw',
    limits=['Initial insertion is not established by a feasible hardware-tightening orientation',
            'Horn and fastener/thread details remain provisional', 'Finite samples; no continuous motion or human grip qualification'])
(HERE / 'reaction_bench_order.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print('REACTION_BENCH', out['bare_initial_gap_mm'], out['preassembled_initial_gap_mm'], out['usable_delayed_fastening_angles_deg'], flush=True)
