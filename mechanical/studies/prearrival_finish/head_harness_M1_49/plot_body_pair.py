"""Show the diagnosed CAM3/4 self-crossing in actual world coordinates."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;OUT=HERE/'remaining_routes/entry_topology_review'
d=json.loads((OUT/'closest_cam34.json').read_text());a=np.load(OUT/'closest_cam34.npz')
r=d['best_pairs'][0];p=np.array(r['point_mm']);q=np.array(r['other_point_mm'])
fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
for ax,(i,j) in zip(axes,[(0,1),(0,2),(1,2)]):
    for key,c in [('a','#e45a40'),('b','#087cab')]:
        curve=a[key];label=d['best_metadata'][key]['endpoint']
        ax.plot(curve[:,i],curve[:,j],c=c,label=label,lw=1.6)
    ax.scatter([p[i],q[i]],[p[j],q[j]],s=50,facecolors='none',edgecolors='#111',zorder=5)
    ax.set(xlabel='XYZ'[i]+' / mm',ylabel='XYZ'[j]+' / mm',title='XYZ'[i]+' / '+'XYZ'[j]+' projection')
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend()
fig.suptitle('Rejected pair: actual centerlines approach within about 0.27 mm\nRequired centerline separation is at least 0.9604 mm before sampling allowance. No printed geometry changed.',fontsize=12)
fig.savefig(OUT/'cam34_overlap.png',dpi=150);plt.close(fig)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'pair_plot_manifest.json').write_text(json.dumps(dict(status='PASS',inputs={p.name:sha(p) for p in [OUT/'closest_cam34.json',OUT/'closest_cam34.npz']},images={'cam34_overlap.png':sha(OUT/'cam34_overlap.png')},script_sha256=sha(Path(__file__)),scope='Rejected route pair visualization, not adopted geometry'),indent=2)+'\n')
print('CAM34_PLOT_DONE')
