"""Actual C6 section comparison, clearly kept separate from the current model."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
HERE=Path(__file__).resolve().parent;OUT=HERE/'remaining_routes/c6_left_slot_entry'
d=json.loads((OUT/'geometry_review.json').read_text());assert d['status']=='PASS' and not d['approved']
def fill(ax,polys,color):
    paths=[]
    for p in polys:
        if len(p)>2:paths.append(MPath(np.vstack([p,p[0]]),[1]+[2]*(len(p)-1)+[79]))
    if paths:ax.add_patch(PathPatch(MPath.make_compound_path(*paths),facecolor=color,edgecolor='#263c46',lw=.6))
xy=next(s for s in d['sections'] if s.get('z_mm')==146.)
rz=next(s for s in d['sections'] if s.get('angle_deg')==125.)
fig,axs=plt.subplots(1,3,figsize=(14,5),layout='constrained')
for ax,k,title in [(axs[0],'old','Current M1.49: slot outer radius 11.7 mm'),(axs[1],'new','Unapproved C6: slot outer radius 12.5 mm')]:
    fill(ax,xy[k],'#607d8b')
    if k=='new':fill(ax,xy['removed'],'#e8aa70')
    ax.set(title=title,xlim=(-16,3),ylim=(-5,17),xlabel='X / mm',ylabel='Y / mm');ax.set_aspect('equal');ax.grid(alpha=.12)
fill(axs[2],rz['new'],'#607d8b');fill(axs[2],rz['removed'],'#e8aa70')
axs[2].set(title='Actual radial section at 125 degrees',xlim=(8,22),ylim=(137,151),xlabel='Radial coordinate / mm',ylabel='Z / mm');axs[2].set_aspect('equal');axs[2].grid(alpha=.12)
axs[2].annotate('Removed outer lip only',xy=(12.1,146.2),xytext=(13.7,141.5),arrowprops=dict(arrowstyle='->'))
fig.suptitle('Study only: widen the existing left passage by 0.8 mm, without changing its angular span\nAmber shows removed material. Bearing seat, keeper axes and all hardware stay at their current positions.',fontsize=12)
fig.savefig(OUT/'section_comparison.png',dpi=150);plt.close(fig)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'plot_manifest.json').write_text(json.dumps(dict(status='PASS',inputs={'geometry_review.json':sha(OUT/'geometry_review.json')},images={'section_comparison.png':sha(OUT/'section_comparison.png')},script_sha256=sha(Path(__file__)),scope='Unapproved candidate visualization only',main_changed=False),indent=2)+'\n')
print('C6_SECTION_PLOT_DONE')
