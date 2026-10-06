"""Plot the recorded current-main horizontal sections, no mesh modification."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
OUT=HERE/'remaining_routes/static_flex'
r=json.loads((OUT/'endpoints.json').read_text())
colors={'Head_Front':'#8b97a2','Head_Rear':'#8b97a2','Pitch_Cradle':'#153b57',
        'Pitch_Yoke':'#22718c','Display_Frame':'#935487','CAM_Mainboard':'#208357',
        'Display_PCB':'#208357','Camera_PCB':'#cf8434','Camera_Lens':'#cf8434',
        'Yaw_Servo':'#cc4747','Pitch_Servo':'#cc4747','Yaw_Base':'#588aaa',
        'Yaw_Bearing':'#588aaa','Yaw_Reaction_Link':'#588aaa'}
fig,axes=plt.subplots(2,3,figsize=(14,10),layout='constrained')
for ax,s in zip(axes.flat,r['sections']):
    for name,polys in s['layers'].items():
        for poly in polys:
            x=[p[0] for p in poly];y=[p[1] for p in poly]
            ax.plot(x+[x[0]],y+[y[0]],color=colors.get(name,'#777777'),lw=1.1)
    ax.set(xlim=(-60,60),ylim=(-60,60),aspect='equal',title=f"Z = {s['z_mm']:.0f} mm",
           xlabel='X right / mm',ylabel='Y forward / mm')
    ax.grid(alpha=.15)
handles=[plt.Line2D([0],[0],color=colors[n],label=n) for n in
    ['Head_Front','Pitch_Cradle','Pitch_Yoke','Display_Frame','CAM_Mainboard','Yaw_Servo']]
fig.legend(handles=handles,loc='outside lower center',ncol=3)
fig.suptitle('M1.49 C5 + K1 — saved-solid sections / no cable-fit claim',fontsize=15)
fig.savefig(OUT/'sections.png',dpi=150)
