"""Inspect public M5Stack reference files without adopting their interfaces.

STL coordinates carry no unit declaration. Section results are model-coordinate
observations, not a dimensioned FEETECH horn drawing or a physical fit result.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
ROOT = A8.parents[3]
OUT = A8 / 'public_source_extensions'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
protected = read(A8 / 'supplier_source_update/verification.json')['protected_files']
for path, digest in protected.items():
    assert sha(ROOT / path) == digest, path

sources = read(OUT / 'retrieval.json')
for row in sources:
    if 'sha256' in row:
        assert sha(OUT / row['file']) == row['sha256']
pdf = OUT / 'm5_scs0009.pdf'
previous = A8.parent / 'supplier_made_harness/sources/SCS0009_A0_mirror.pdf'
assert sha(pdf) == sha(previous)
directory = read(OUT / 'm5_structure_directory.json')
arm_entry = next(row for row in directory if row['name'] == 'StackChan-ServoArm.stl')
stl = OUT / arm_entry['name']
raw = stl.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
assert git_blob == arm_entry['sha']
count = int.from_bytes(raw[80:84], 'little')
assert len(raw) == 84 + 50 * count
dtype = np.dtype([('normal', '<f4', (3,)), ('v', '<f4', (3, 3)), ('attr', '<u2')])
triangles = np.frombuffer(raw, dtype=dtype, count=count, offset=84)['v'].astype(float)
low, high = triangles.min(axis=(0, 1)), triangles.max(axis=(0, 1))

# A section inside the visibly toothed cylindrical portion; retain both loops.
section_x = 331.0
adj, coordinates = {}, {}
for triangle in triangles:
    signed = triangle[:, 0] - section_x
    hits = []
    for a, b in [(0, 1), (1, 2), (2, 0)]:
        if signed[a] * signed[b] < 0:
            t = -signed[a] / (signed[b] - signed[a])
            hits.append((triangle[a] + t * (triangle[b] - triangle[a]))[1:])
    if len(hits) != 2:
        continue
    a, b = hits
    ka, kb = tuple(np.round(a, 5)), tuple(np.round(b, 5))
    adj.setdefault(ka, []).append(kb)
    adj.setdefault(kb, []).append(ka)
    coordinates[ka], coordinates[kb] = a, b
assert all(len(neighbours) == 2 for neighbours in adj.values())
seen, loops = set(), []
for start in adj:
    if start in seen:
        continue
    previous_key, key, loop = None, start, []
    while key not in seen:
        seen.add(key)
        loop.append(coordinates[key])
        choices = adj[key]
        next_key = choices[0] if choices[0] != previous_key else choices[1]
        previous_key, key = key, next_key
    assert key == start
    loops.append(np.asarray(loop))
assert len(loops) == 2
inner = min(loops, key=lambda q: np.prod(np.ptp(q, axis=0)))
center = (inner.min(axis=0) + inner.max(axis=0)) / 2
radius = np.linalg.norm(inner - center, axis=1)
angle = np.mod(np.arctan2(inner[:, 1] - center[1], inner[:, 0] - center[0]), 2 * np.pi)
order = np.argsort(angle)
sample_angles = np.linspace(0, 2 * np.pi, 20480, endpoint=False)
samples = np.interp(sample_angles, angle[order], radius[order], period=2 * np.pi)
dominant_harmonic = int(np.argmax(abs(np.fft.rfft(samples - samples.mean()))[1:]) + 1)

fig, ax = plt.subplots(figsize=(7, 7), layout='constrained')
for loop in loops:
    q = np.vstack([loop, loop[0]]) - center
    ax.plot(q[:, 0], q[:, 1], linewidth=1.1, color='#31596b')
ax.set(aspect='equal', xlabel='Y, source STL coordinate', ylabel='Z, source STL coordinate',
       title='M5Stack ServoArm section at X = 331\nReference geometry; units and MORI compatibility unqualified')
ax.grid(alpha=.2)
fig.savefig(OUT / 'm5_arm_section.png', dpi=140)
plt.close(fig)
fig = plt.figure(figsize=(12, 6), layout='constrained', facecolor='#edf2f4')
mid, half = (low + high) / 2, float(np.max(high - low)) / 2
for i, (elevation, azimuth) in enumerate([(28, -65), (-35, 115)]):
    ax = fig.add_subplot(1, 2, i + 1, projection='3d')
    ax.add_collection3d(Poly3DCollection(triangles, facecolors='#90a6b1',
                                       edgecolors='#566773', linewidths=.08))
    ax.set(xlim=(mid[0]-half, mid[0]+half), ylim=(mid[1]-half, mid[1]+half),
           zlim=(mid[2]-half, mid[2]+half))
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elevation, azimuth)
    ax.set_axis_off()
fig.suptitle('M5Stack ServoArm - original STL, unscaled reference', fontsize=14)
fig.savefig(OUT / 'm5_arm_views.png', dpi=140)
plt.close(fig)

source_files = {str(p.relative_to(ROOT)): sha(p) for p in [
    SCRIPT, previous, OUT/'retrieval.json', pdf, stl, OUT/'m5_structure_directory.json',
    OUT/'m5_scs0009_page7.png', OUT/'jst_de_terminal.html', OUT/'jst_de_housing.html',
    OUT/'additional_retrievals.json']}
report = dict(status='PASS', scope='Source identity and reference STL inspection only',
    generated_utc=datetime.now(timezone.utc).isoformat(), protected_files=protected,
    source_files=source_files, source_pdf_matches_existing=True,
    pdf_edition='FEETECH SCS0009 A/0, 2020-11-23',
    accessories_page='No Accessories, page 7/8; not a vendor horn drawing',
    repository_part='M5Stack StackChan-ServoArm.stl', git_blob_sha1=git_blob,
    part_classification='PURCHASED_REFERENCE', exact_MORI_interface_evidence='ASSUMED',
    triangle_count=count, coordinate_bounds=[low.tolist(),high.tolist()],
    coordinate_extents=(high-low).tolist(), STL_units='NOT_DOCUMENTED',
    section_x_coordinate=section_x, closed_section_loops=len(loops),
    inner_boundary_coordinate_extents=np.ptp(inner,axis=0).tolist(),
    inner_boundary_vertex_radius_range=[float(radius.min()),float(radius.max())],
    dominant_radial_harmonic=dominant_harmonic,
    section_note='Radial harmonic is a mesh observation, not a spline tooth standard, tolerance or compatibility certificate',
    jst_german_pages='Retrieved with system curl certificate verification; specification tables only, no part CAD/drawing links found',
    main_applied=False, complete_servo_horn_interface='BLOCKED', manufacturing_release=False,
    outputs={name:sha(OUT/name) for name in ['m5_arm_views.png','m5_arm_section.png']})
(OUT/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for path,digest in protected.items():
    assert sha(ROOT/path)==digest,path
print(json.dumps({k:report[k] for k in ['status','source_pdf_matches_existing','triangle_count',
    'inner_boundary_coordinate_extents','dominant_radial_harmonic','complete_servo_horn_interface']}))
