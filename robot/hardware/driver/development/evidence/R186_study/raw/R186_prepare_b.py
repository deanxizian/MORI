"""Bind the pair screen to native guard types before building a prep candidate.

Keep the generated, unbuilt plan as evidence. All four parts have a single
combined track/via body guard: move it rigidly, with no fixed-cutout operation.
Only exactly collinear intermediate route points are removed.
"""
import copy, json, math, sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper
b = Path('robot/.state/c3-completion/trials')
path = b/'R186B-plan.json'
original = path.read_bytes()
archive = b/'R186B-generated-unbuilt-plan.json'
assert not archive.exists() and not (b/'R186B').exists()
plan = json.loads(original)
c = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert plan['board_sha256'] == c.sha
guards = {}
for row in plan['translations']:
    owned = [k for k in c.keepouts if k['name'].startswith('BODY_'+row['reference']+'_')]
    assert len(owned) == 1 and owned[0]['tracks'] and owned[0]['vias']
    guards[row['reference']] = owned[0]['name']
    for key in ['reconstruct_fixed_via_guards', 'rotate_fixed_via_guards', 'repartition_fixed_via_guards']:
        row.pop(key)
for row in plan['routes']:
    points = []
    for point in row['points_mm']:
        while len(points) >= 2:
            a,z = points[-2:]
            v = [z[i]-a[i] for i in range(2)]
            w = [point[i]-z[i] for i in range(2)]
            if abs(v[0]*w[1]-v[1]*w[0]) < 1e-10 and sum(v[i]*w[i] for i in range(2)) > 0:
                points.pop()
            else:
                break
        points.append(point)
    row['points_mm'] = points
plan['scope'] += '\nNative combined guards move rigidly; this preparation leaves terminal reconnections open.'
archive.write_bytes(original)
path.write_text(json.dumps(plan, indent=2)+'\n')
(b/'R186B-plan-preparation.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,
    native_guard_types=guards,generated_plan_built=False,physical='NOT_TESTED'),indent=2)+'\n')
print(json.dumps(dict(status='PREPARATION_ONLY',guards=guards,moves=plan['translations'],routes=plan['routes'])))
