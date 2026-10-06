"""Readable real-solid sections; no image retouching or inferred surfaces."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
d=json.loads((HERE/'route_sections.json').read_text())
colors={'Yaw_Base':'#718e9c','Yaw_Reaction_Link':'#c29157','Pitch_Yoke':'#8ca99a',
        'Yaw_Bearing':'#89909e','Yaw_Servo':'#deceaa','Pitch_Servo':'#d9c0a0'}
def fill(ax,polys,color,alpha=1):
    vs=[];cs=[]
    for p in polys:
        if len(p)<3:continue
        vs.extend(p+[p[0]]);cs.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY])
    if vs:ax.add_patch(PathPatch(PlotPath(vs,cs),facecolor=color,edgecolor='#34434a',lw=.5,alpha=alpha))
fig,axes=plt.subplots(2,2,figsize=(13,10),dpi=145)
for ax,angle in zip(axes.flat,[0,45,90,135]):
    for name,polys in d['sections'][str(angle)].items():
        if name.startswith('lower_') or name=='upper_pose_union':continue
        fill(ax,polys,colors.get(name,'#dadde0'))
    ax.set(xlim=(-28,28),ylim=(179,210),aspect='equal',title=f'上端真实零位剖面 · 方位 {angle}°',xlabel='有符号径向 / mm',ylabel='Z / mm')
    ax.grid(alpha=.15)
fig.legend([Patch(facecolor=c) for c in colors.values()],list(colors),loc='lower center',ncol=3,fontsize=9)
fig.suptitle('UART 上端进出：反力件、头座和舵机的实际剖面',fontsize=16)
fig.tight_layout(rect=[0,.075,1,.96])
fig.savefig(HERE/'upper_route_sections.png',facecolor='#f7f8f7');plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(15,6),dpi=145)
layer=d['sections']['45']
for ax,name,label in zip(axes,['Yaw_Base','lower_C1','lower_C2'],['当前主模型','C1：弯槽，存在薄残边风险','C2：局部开通屋面，待审核']):
    fill(ax,layer[name],colors['Yaw_Base'])
    for part in ['Yaw_Reaction_Link','Yaw_Bearing']:
        fill(ax,layer.get(part,[]),colors[part])
    R=8.;t=np.linspace(0,np.pi/2,201);r=6.8+R*(1-np.cos(t));z=150-R*np.sin(t)
    for s in [-1,1]:
        ax.plot(s*r,z,color='#b32438',lw=1.3)
        ax.plot([s*(6.8+R),s*24],[142,142],color='#b32438',lw=1.3)
    ax.set(xlim=(-20,20),ylim=(136,157),aspect='equal',title=label,xlabel='45° 有符号径向 / mm',ylabel='Z / mm')
    ax.grid(alpha=.15)
fig.suptitle('下端候选：只改独立副本，主模型未修改',fontsize=16)
fig.text(.07,.085,'红线是候选导线中心线（Ø0.6604 mm，弯曲半径8 mm）。C2对轴座承压和剩余材料的影响尚待审查。',fontsize=11)
fig.tight_layout(rect=[0,.15,1,.93]);fig.savefig(HERE/'lower_entry_sections.png',facecolor='#f7f8f7');plt.close(fig)
print('ROUTE_SECTION_PLOTS_SAVED')
