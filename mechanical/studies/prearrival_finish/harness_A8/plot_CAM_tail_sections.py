"""Plot actual Z212 sections against old work box and saved strip projection."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,Patch
from matplotlib.collections import PolyCollection
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'cam_tail_ribbon'
d=json.loads((OUT/'sections.json').read_text())
a=np.load(OUT/'inner_tail_34.npz')
colors={'Pitch_Yoke':'#678694','Pitch_Cradle':'#d6e0e3','Yaw_Servo':'#9cabb0',
        'Pitch_Servo':'#9cabb0','CAM_connector_tie_head':'#d8af55','CAM_connector_tie_band':'#efd38f'}
fig,axes=plt.subplots(1,2,figsize=(12,8.4),layout='constrained')
for ax in axes:
    for row in d['sections']['212.0']:
        for poly in row['polygons']:
            ax.add_patch(Polygon(poly,facecolor=colors[row['name']],edgecolor='#33454f',linewidth=.55))
    ax.set(xlim=(-50,12),ylim=(-38,38),xlabel='X (mm)',ylabel='Y (mm)');ax.set_aspect('equal')
    ax.grid(alpha=.18);ax.set_axisbelow(True)
    ax.annotate('CAM tie',xy=(-15.9,-19.16),xytext=(-47,-25),arrowprops={'arrowstyle':'->'},fontsize=10)
    ax.text(-26,0,'Pitch servo',ha='center',va='center',fontsize=9)
    ax.text(0,1,'Yaw\nservo',ha='center',va='center',fontsize=9)
axes[0].add_patch(Rectangle((-18.9,-19.16),6,110,facecolor='#e44940',edgecolor='#ba231d',alpha=.36))
axes[0].set_title('Earlier straight working area\n6 x 110 x 2.7 mm (ASSUMED)',fontsize=12)
axes[1].add_collection(PolyCollection(a['vertices_mm'][a['triangles']][:,:,:2],facecolor='#e9a226',edgecolor='none'))
axes[1].set_title('Temporary flexible-tail route\n1.3 x 2.7 mm upper cross-section',fontsize=12)
axes[1].annotate('Through existing gap',xy=(-34,0),xytext=(-48,23),arrowprops={'arrowstyle':'->'},fontsize=10)
fig.suptitle('CAM tie tail: section at Z = 212 mm\nRobot solids and four CAM wires unchanged',fontsize=16)
fig.text(.5,.005,'Tail continues beyond the plot; full 110 mm allocation checked. Shape and R5 bends are assumptions, not material qualification.',ha='center',fontsize=9)
fig.savefig(OUT/'tail_section_comparison.png',dpi=160)
fig.savefig(OUT/'tail_section_comparison.svg')
print('TAIL_SECTION_PLOT_DONE')
