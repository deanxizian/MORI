"""Inspect body wiring layers before choosing bounded-curvature routes."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as P
from matplotlib.patches import PathPatch,Patch
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent;OUT=HERE/'body_prefix_v2'
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False})
d=json.loads((OUT/'corridors.json').read_text())
ports=json.loads((HERE/'h06_ports.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(16,6.2),dpi=145)
for ax,z in zip(axes,[139.,142.63999938964844,146.]):
    for row in d['rows']:
        polys=row['sections'].get(str(z),[])
        color=('#dfa251' if row['id'].startswith('H0') else '#709cac' if row['id'].startswith('Yaw_') else '#c5cbd0')
        if row['id'].startswith('Plug_'):color='#cdacb8'
        vv=[];cc=[]
        for poly in polys:
            if len(poly)<3:continue
            vv+=poly+[poly[0]];cc+=[P.MOVETO]+[P.LINETO]*(len(poly)-1)+[P.CLOSEPOLY]
        if vv:ax.add_patch(PathPatch(P(vv,cc),fc=color,ec='#53636a',lw=.3,alpha=.85))
    for angle in [45,135,225,315]:
        a=math.radians(angle);r=np.array([math.cos(a),math.sin(a)])
        for radius in [14.8,24.2]:ax.scatter(*(r*radius),s=12,color='#8b245d',zorder=5)
        ax.text(*(r*30),str(angle)+'°',ha='center',fontsize=9,color='#791e4d')
    for pin,p in ports['body']['pins'].items():ax.scatter(*p[:2],s=16,color='#c51d44',zorder=6)
    ax.set(xlim=(-70,70),ylim=(-75,65),aspect='equal',title=f'Z = {z:.2f} mm',xlabel='X / mm',ylabel='Y / mm');ax.grid(alpha=.12)
fig.suptitle('身体引线：实际实体在 ±0.631 mm 高度带内的投影',fontsize=16)
fig.legend([Patch(fc=c) for c in ['#709cac','#dfa251','#cdacb8','#c5cbd0']],['偏航承重与传动','既有14根静态线候选','对插空间','其他结构/硬件'],loc='lower center',ncol=4,bbox_to_anchor=(.5,.065))
fig.text(.04,.025,'二维投影用于选路，尚未作XY间隙扩张；通过与否由三维实体、实际线径和弯曲半径复核。',fontsize=11)
fig.tight_layout(rect=[0,.15,1,.94]);fig.savefig(OUT/'corridors.png',facecolor='#f5f7f7');plt.close(fig)
