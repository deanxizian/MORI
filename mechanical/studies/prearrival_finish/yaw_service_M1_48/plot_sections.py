from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as PlotPath
import numpy as np
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'sections.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(14,6),layout='constrained')
colors={'Yaw_Base':'#8199a2','Pitch_Yoke':'#577e8b','Yaw_Reaction_Link':'#343b42',
        'Yaw_Bearing':'#b7bec2','Yaw_Anti_Lift_Keeper':'#8e9295',
        'Yaw_Base_removed':'#ef7057','Pitch_Yoke_removed':'#ef7057'}
for ax,key,title in zip(axes,['radial45','Z152.5','Z188.0'],
                        ['45-degree radial section','Bearing journal: Z152.5','Upper exit: Z188']):
    for name,color in colors.items():
        paths=[]
        for polygon in d[key].get(name,[]):
            if len(polygon)>2:
                vertices=np.vstack([polygon,polygon[0]])
                codes=[PlotPath.MOVETO]+[PlotPath.LINETO]*(len(polygon)-1)+[PlotPath.CLOSEPOLY]
                paths.append(PlotPath(vertices,codes))
        if paths:ax.add_patch(PathPatch(PlotPath.make_compound_path(*paths),facecolor=color,edgecolor=color,linewidth=.55,alpha=.75))
    ax.set_title(title);ax.set_aspect('equal');ax.grid(alpha=.15)
    if key=='radial45':ax.set_xlim(-23,23);ax.set_ylim(135,195);ax.set_xlabel('Radial X (mm)');ax.set_ylabel('Z (mm)')
    else:ax.set_xlim(-15,15);ax.set_ylim(-15,15);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
fig.suptitle('Unadopted channel candidate | red = removed from native M1.48\nNo raised anchors copied; section samples do not certify PA12 strength',fontsize=13)
fig.savefig(HERE/'channel_sections.png',dpi=150)
