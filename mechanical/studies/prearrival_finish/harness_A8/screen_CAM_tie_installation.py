"""Screen an oriented T18R installation allocation, never product latch CAD.

The public drawings locate the strap on one side of the head and show a
through-head opening normal to the flat strap. Aperture centre and the formed
strap are assumptions. A full head box is retained for obstacle checks.
"""
from pathlib import Path
TIE_SCRIPT = Path(__file__).resolve()
TIE_A8 = TIE_SCRIPT.parent
TIE_HELPER = TIE_A8 / 'screen_CAM_anchor_support.py'
__file__ = str(TIE_HELPER)
exec(compile(TIE_HELPER.read_text().split('\nhost=ss[', 1)[0], str(TIE_HELPER), 'exec'), globals())
__file__ = str(TIE_SCRIPT)
TIE_OUT = TIE_A8 / 'cam_tie_install'
TIE_OUT.mkdir(exist_ok=True)

def stored(path):
    a = np.load(path)
    m = manifold.Manifold(manifold.Mesh64(a['vertices_mm'], a['triangles']))
    assert m.status() == manifold.Error.NoError
    return m

TIE_HOST = stored(TIE_A8 / 'cam_anchors/candidate_v3/cleaned/Pitch_Yoke.npz')
TIE_Z = 232.0
TIE_WIDTH = 2.7
TIE_THICKNESS = 1.3
TIE_LEFT = float(xx.min() - 1.2)
TIE_RIGHT = float(xx.max() + 1.2)
TIE_HEAD_LEFT = TIE_RIGHT + .5
TIE_HEAD_FRONT = .14
TIE_HEAD_BACK = TIE_HEAD_FRONT - 4.3
TIE_CAVITY_X = TIE_HEAD_LEFT + 2.6  # CSH drawing proportion, not a dimension.
TIE_HEAD = box([TIE_HEAD_LEFT, TIE_HEAD_BACK, TIE_Z - 2.5],
               [TIE_HEAD_LEFT + 5.3, TIE_HEAD_FRONT, TIE_Z + 2.5])

def ribbon(rear_y, end_y):
    """Flat strap in XY, width along Z; analytic tangent-continuous arcs."""
    radius = 1.25
    pts, normals = [], []
    def emit(p, tangent):
        if pts and np.linalg.norm(np.asarray(p) - pts[-1]) < 1e-9:
            return
        pts.append(np.array(p, float))
        normals.append(np.array([-tangent[1], tangent[0]], float))
    def line(p, q):
        p, q = np.array(p), np.array(q)
        direction = (q-p) / np.linalg.norm(q-p)
        for t in np.linspace(0, 1, max(2, int(np.ceil(np.linalg.norm(q-p)/.1))+1)):
            emit(p+(q-p)*t, direction)
    def arc(c, a, b):
        for theta in np.linspace(a, b, 65):
            emit(np.array(c)+radius*np.array([math.cos(theta), math.sin(theta)]),
                 [-math.sin(theta), math.cos(theta)])
    front_y = TIE_HEAD_FRONT - TIE_THICKNESS/2
    xleft = TIE_LEFT + .6
    line([TIE_HEAD_LEFT + .01, front_y], [xleft, front_y])
    arc([xleft, front_y-radius], math.pi/2, math.pi)
    line([xleft-radius, front_y-radius], [xleft-radius, rear_y+radius])
    arc([xleft, rear_y+radius], math.pi, 3*math.pi/2)
    line([xleft, rear_y], [TIE_CAVITY_X-radius, rear_y])
    arc([TIE_CAVITY_X-radius, rear_y+radius], 3*math.pi/2, 2*math.pi)
    line([TIE_CAVITY_X, rear_y+radius], [TIE_CAVITY_X, end_y])
    pts, normals = np.array(pts), np.array(normals)
    polygon = np.vstack([pts+TIE_THICKNESS/2*normals,
                         (pts-TIE_THICKNESS/2*normals)[::-1]])
    signed_area = .5*np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1))
    if signed_area < 0:
        polygon = polygon[::-1]
    m = manifold.CrossSection([polygon.tolist()]).extrude(TIE_WIDTH).translate([0,0,TIE_Z-TIE_WIDTH/2])
    # Analytic arclength: three quarter circles plus the five straight segments.
    lengths = [TIE_HEAD_LEFT+.01-xleft,
               (front_y-radius)-(rear_y+radius),
               TIE_CAVITY_X-radius-xleft,
               end_y-(rear_y+radius)]
    assert min(lengths) >= 0
    arclength = sum(lengths) + 3*math.pi*radius/2
    assert m.status() == manifold.Error.NoError and m.volume() > 1.
    assert len(m.decompose()) == 1
    assert abs(float(m.volume())-arclength*TIE_THICKNESS*TIE_WIDTH) < .02
    return m, pts, arclength

# Orienting the head changes the strap envelope. Check both solids and all
# previously checked nominal CAM wires before proposing an installation path.
trials = []
for rear in [-5.4, -6.5, -7.0, -8.0]:
    band, points, length = ribbon(rear, TIE_HEAD_FRONT)
    tie = band + TIE_HEAD
    row = {'rear_centreline_y_mm': rear, 'head_bounds_mm': list(TIE_HEAD.bounding_box()),
           'assumed_cavity_x_mm': TIE_CAVITY_X,
           'strap_centreline_length_to_head_exit_mm': length,
           'strap_volume_mm3': float(band.volume()),
           'analytic_strap_volume_mm3': length*TIE_THICKNESS*TIE_WIDTH,
           'strap_components': len(band.decompose()),
           'tail_remaining_lower_allocation_mm': 95.0-5.3-length,
           'formed_strap_evidence': 'ASSUMED',
           'source': source_fit(tie), 'wires': wire_fit(tie),
           'yoke_intersection_mm3': max(0., float((tie ^ TIE_HOST).volume()))}
    row['status'] = ('PASS' if row['source']['status'] == row['wires']['status'] == 'PASS'
                     and row['yoke_intersection_mm3'] < .001 else 'BLOCKED')
    trials.append(row)
    print('ORIENTED_TIE', row, flush=True)
    cache(TIE_OUT / f'band_{len(trials)-1}.npz', band)

accepted = [i for i, row in enumerate(trials) if row['status'] == 'PASS']
cache(TIE_OUT/'head_allocation.npz', TIE_HEAD)
report = {'status': 'PASS' if accepted else 'BLOCKED',
          'scope': 'Oriented installed tie allocation; latch channel and formed shape assumed',
          'source_main_sha256': source_hash,
          'candidate_sha256': sha(TIE_A8/'cam_anchors/candidate_v3/cleaned/candidate.blend'),
          'script_sha256': sha(TIE_SCRIPT),
          'band_width_upper_mm': TIE_WIDTH, 'band_thickness_upper_mm': TIE_THICKNESS,
          'trials': trials, 'accepted_indices': accepted,
          'actual_latch_and_channel': 'NOT_TESTED', 'physical_bend_and_grip': 'NOT_TESTED',
          'whole_harness': 'BLOCKED', 'main_applied': False}
(TIE_OUT/'oriented_tie_screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert sha(source) == source_hash
print('ORIENTED_TIE_DONE', report['status'], accepted, flush=True)
