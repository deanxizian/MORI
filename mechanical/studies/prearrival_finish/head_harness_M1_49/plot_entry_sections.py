"""Publish actual solid sections extracted by inspect_entry_sections.py."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
HERE=Path(__file__).resolve().parent;OUT=HERE/'remaining_routes/entry_topology_review'
d=json.loads((OUT/'sections.json').read_text());curves=np.load(OUT/'representative_curves.npz')
colors={'Yaw_Base':'#516778','Yaw_Bearing':'#c8a14b','Pitch_Yoke':'#83b7aa','Yaw_Anti_Lift_Keeper':'#d4a083','Yaw_Reaction_Link':'#c4d0d8','Power_Module':'#a0b09b','MCU_Carrier':'#a0b09b'}
def solid(ax,polygons,color):
    paths=[]
    for points in polygons:
        p=np.asarray(points)
        if len(p)<3:continue
        paths.append(MPath(np.vstack([p,p[0]]),[MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY]))
    if paths:ax.add_patch(PathPatch(MPath.make_compound_path(*paths),fc=color,ec='#263640',lw=.5))
fig,axs=plt.subplots(2,3,figsize=(14,9),layout='constrained')
for ax,s in zip(axs.flat,[x for x in d['sections'] if x['kind']=='XY']):
    for name,polygons in s['solids'].items():solid(ax,polygons,colors.get(name,'#aaa'))
    for key,p in curves.items():
        col='#e45146' if '149' in key else '#007fb5'
        ax.plot(p[:,0],p[:,1],c=col,lw=.7,alpha=.45)
        v=p[abs(p[:,2]-s['z_mm'])<.3]
        if len(v):ax.scatter(v[:,0],v[:,1],s=3,c=col,zorder=4)
    ax.set(title=f"Actual XY section Z = {s['z_mm']:g} mm",xlim=(-38,38),ylim=(-52,30),xlabel='X / mm',ylabel='Y / mm')
    ax.set_aspect('equal');ax.grid(alpha=.15)
fig.suptitle('Fixed neck entry: actual sections and representative route projections\nBlue: entry Z142; red: rejected raised entry Z149. Dots: within 0.3 mm of section. Main unchanged.',fontsize=12)
fig.savefig(OUT/'xy_sections.png',dpi=145);plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
for ax,s in zip(axs.flat,[x for x in d['sections'] if x['kind']=='RZ']):
    for name,polygons in s['solids'].items():solid(ax,polygons,colors.get(name,'#aaa'))
    ax.axvline(10.6,c='#d35400',ls='--',lw=1,label='planned entry radius 10.6')
    ax.axhline(142,c='#007fb5',ls=':',lw=1);ax.axhline(149,c='#e45146',ls=':',lw=1)
    ax.set(title=f"Actual radial section at {s['angle_deg']:g} degrees",xlim=(0,27),ylim=(128,170),xlabel='Radial coordinate / mm',ylabel='Z / mm')
    ax.set_aspect('equal');ax.grid(alpha=.15)
fig.suptitle('The annular entry is approached from below; raising a side-entry arc crosses retained material\nBlue lines: Z142. Red lines: Z149. No channel modification proposed or adopted.',fontsize=12)
fig.savefig(OUT/'radial_sections.png',dpi=160);plt.close(fig)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'plot_manifest.json').write_text(json.dumps(dict(status='PASS',source_sha256=sha(OUT/'sections.json'),
    curve_sha256=sha(OUT/'representative_curves.npz'),images={p.name:sha(p) for p in [OUT/'xy_sections.png',OUT/'radial_sections.png']},
    script_sha256=sha(Path(__file__)),scope='Visualization only; curves are projections, sections are actual solids',main_changed=False),indent=2)+'\n')
print('ENTRY_PLOTS_DONE')
