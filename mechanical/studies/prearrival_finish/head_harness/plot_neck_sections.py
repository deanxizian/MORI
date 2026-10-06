"""Draw existing-solid cross sections, without interpreting white as a route."""
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
d=json.loads((HERE/'neck_sections.json').read_text())
colors={'body':'#c6d2dc','yaw':'#74a9aa','pitch':'#dfbb8f'}
def shape(polygons):
    v=[];c=[]
    for p in polygons:
        if len(p)<3:continue
        v+=p+[p[0]];c += [PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY]
    return PlotPath(v,c)
fig,axs=plt.subplots(2,5,figsize=(17,8),dpi=140)
for ax,row in zip(axs.flat,d['sections']):
    for name,layer in row['layers'].items():
        ax.add_patch(PathPatch(shape(layer['polygons_mm']),facecolor=colors.get(layer['group'],'#cdd3d7'),edgecolor='#425b66',lw=.45))
    ax.set(xlim=(-36,36),ylim=(-36,36),aspect='equal',title=f"Z = {row['z_mm']:g} mm",xticks=[-30,0,30],yticks=[-30,0,30])
    ax.axhline(0,color='#7d919b',lw=.5,ls=':');ax.axvline(0,color='#7d919b',lw=.5,ls=':')
fig.suptitle('现有转头关节：各高度实体剖面',fontsize=20,x=.05,ha='left')
fig.legend([Patch(facecolor=colors[g]) for g in colors],['固定身体','随 yaw 转动','随 yaw＋pitch 转动'],loc='upper right',ncol=3,bbox_to_anchor=(.96,.965),frameon=False)
fig.text(.055,.026,'XY 坐标 / mm；+Y 向前。空白仅表示该截面没有实体，不代表壳内连通通道，也不表示线束能通过。',fontsize=12,color='#536973')
fig.subplots_adjust(left=.045,right=.975,top=.86,bottom=.09,wspace=.27,hspace=.23)
for ext in ['png','svg']:fig.savefig(HERE/('neck_sections.'+ext),facecolor='#f6f8f8')
plt.close(fig)
fig,ax=plt.subplots(figsize=(10,9),dpi=160)
for name,layer in d['side_section']['layers'].items():
    ax.add_patch(PathPatch(shape(layer['polygons_mm']),facecolor=colors.get(layer['group'],'#cdd3d7'),edgecolor='#425b66',lw=.6))
ax.set(xlim=(-62,-1),ylim=(135,194),aspect='equal',xlabel='Y / mm（向前 →）',ylabel='Z / mm',title='X = 0 后侧颈部剖面')
ax.grid(alpha=.15)
fig.text(.11,.03,'白色为该切面的空处；还需核对三维距离、转弯、运动、固定和装配。',fontsize=11)
fig.subplots_adjust(bottom=.13,top=.92)
for ext in ['png','svg']:fig.savefig(HERE/('neck_side.'+ext),facecolor='#f6f8f8')
print('NECK_SECTION_PLOTS',len(d['sections']))
