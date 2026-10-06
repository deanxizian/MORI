"""Render exact candidate sections; no model mutation."""
from pathlib import Path
import hashlib
import json
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
import numpy as np

HERE = Path(__file__).resolve().parent
report = json.loads((HERE / 'thin_candidate_check.json').read_text())
assert not report['applied_to_main']
parser=argparse.ArgumentParser();parser.add_argument('--approved-only',action='store_true');args=parser.parse_args()
audit=None
if args.approved_only:
    audit=json.loads((HERE.parents[1]/'reports/approved_thin_cleanup_validation.json').read_text())
    assert audit['status']=='PASS' and audit['approved_candidate_sha256']==report['candidate_blend_sha256']
    assert audit['source_blend_sha256']==hashlib.sha256((HERE.parents[1]/'mori_v1_2.blend').read_bytes()).hexdigest()
    assert all(row['candidate_difference_mm3']==0 for row in audit['solids'])
specs = [
    ('Pitch_Yoke', 'candidate_yoke.png', 'Retired nut channels filled', None),
    ('Yaw_Reaction_Link', 'candidate_reaction.png', 'Reaction clamp: lower wall +1 mm', ((-13, 13), (187, 198))),
    ('Motor_Retainer', 'candidate_cap.png', 'Motor cap saddle: 18 to 19.2 mm', ((-11, 11), (32, 57))),
]
if args.approved_only:
    specs=[(part,name.replace('candidate_','approved_M1_47_'),title,bounds) for part,name,title,bounds in specs if part!='Yaw_Reaction_Link']
saved = []
for part, name, title, bounds in specs:
    rows = [r for r in report['sections'] if r['id'] == part]
    fig, axes = plt.subplots(len(rows), 2, figsize=(10, 4.6 * len(rows)), squeeze=False)
    for i, row in enumerate(rows):
        for j, state in enumerate(['before', 'after']):
            vertices, codes = [], []
            for poly in row[state]:
                pts = np.asarray(poly)
                vertices.extend(pts.tolist() + [pts[0].tolist()])
                codes.extend([PlotPath.MOVETO] + [PlotPath.LINETO] * (len(pts)-1) + [PlotPath.CLOSEPOLY])
            ax = axes[i, j]
            ax.add_patch(PathPatch(PlotPath(vertices, codes), facecolor=['#849599', '#377b70'][j], edgecolor='#173c38', linewidth=.9))
            allpts = np.asarray([p for s in ['before', 'after'] for poly in row[s] for p in poly])
            if bounds:
                ax.set_xlim(*bounds[0]); ax.set_ylim(*bounds[1])
            else:
                low, high = allpts.min(0)-2, allpts.max(0)+2
                ax.set_xlim(low[0], high[0]); ax.set_ylim(low[1], high[1])
            ax.set_aspect('equal'); ax.grid(alpha=.17)
            ax.set_xlabel(('−' if row['x_sign'] == -1 else '')+'XYZ'[row['plane_axes'][0]]+' (mm)')
            ax.set_ylabel('XYZ'[row['plane_axes'][1]]+' (mm)')
            labels=['Before M1.46','M1.47 - APPLIED'] if args.approved_only else ['Current M1.46','Candidate · NOT APPLIED']
            ax.set_title(labels[j] + f"\n{'XYZ'[row['axis']]} = {row['coordinate_mm']} mm")
    fig.suptitle(title, fontsize=16)
    fig.text(.5, .012, 'Exact solid sections · geometry comparison only · PA12 strength unqualified', ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.94),h_pad=3.0); fig.savefig(HERE/name, dpi=150); plt.close(fig)
    saved.append({'file':name,'sha256':hashlib.sha256((HERE/name).read_bytes()).hexdigest()})
record={'source_blend_sha256':report['source_blend_sha256'],'candidate_blend_sha256':report['candidate_blend_sha256'],'images':saved}
if audit:record.update(current_main_sha256=audit['source_blend_sha256'],equality_evidence='../../reports/approved_thin_cleanup_validation.json')
(HERE/('thin_approved_images.json' if args.approved_only else 'thin_comparison_images.json')).write_text(json.dumps(record,indent=2)+'\n')
print('Rendered', [x['file'] for x in saved])
