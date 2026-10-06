"""Illustrate the recorded fixed planning-probe failure at two actual poses."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Polygon,Patch
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
read=lambda name:json.loads((HERE/name).read_text())
d=read('neck_motion_sections.json');seed=read('outer_neck_turn.json')
points=np.asarray(seed['selected'][0]['curve_mm'])[:,1:]
radius=seed['selected'][0]['probe_diameter_mm']/2+seed['project_gap_per_side_mm']
tangents=np.gradient(points,axis=0);tangents/=np.linalg.norm(tangents,axis=1)[:,None]
normal=np.column_stack([-tangents[:,1],tangents[:,0]])
band=np.vstack([points+radius*normal,(points-radius*normal)[::-1]])
def shape(polygons):
    vv=[];cc=[]
    for p in polygons:
        if len(p)<3:continue
        vv+=p+[p[0]];cc += [PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY]
    return PlotPath(vv,cc)
colors={'body':'#c6d2dc','yaw':'#74a9aa','pitch':'#dfbb8f'}
fig,axs=plt.subplots(1,2,figsize=(13,7),dpi=160)
for ax,row in zip(axs,d['sections']):
    for name,layer in row['layers'].items():
        ax.add_patch(PathPatch(shape(layer['polygons_mm']),facecolor=colors.get(layer['group'],'#cdd3d7'),edgecolor='#48616a',lw=.6))
    ax.add_patch(Polygon(band,facecolor='#b65252',alpha=.36,edgecolor='#963535',lw=.5))
    ax.plot(points[:,0],points[:,1],color='#942b31',lw=1.2)
    ax.set(xlim=(-56,-14),ylim=(139,183),aspect='equal',xlabel='Y / mm（向前 →）',ylabel='Z / mm')
    ax.set_title('零位：试算段静态通过' if row['pitch_deg']==0 else '抬头 20°：后壳扫到固定试算段',fontsize=14)
    ax.grid(alpha=.13)
fig.suptitle('颈部不能只按零位布线',x=.07,ha='left',fontsize=21)
fig.legend([Patch(facecolor=colors[g]) for g in colors]+[Patch(facecolor='#b65252',alpha=.5)],
    ['固定身体','随 yaw 转动','随 yaw＋pitch 转动','3 mm 圆束试算＋每侧 0.3 mm 余量'],
    loc='upper center',bbox_to_anchor=(.51,.94),ncol=4,frameon=False)
fig.text(.075,.04,'X = 0 实体剖面。红色是规划占位，不是已选线束；曲线端点未固定，完整动态路线尚未完成。',fontsize=11,color='#536973')
fig.subplots_adjust(top=.81,bottom=.14,left=.06,right=.97,wspace=.23)
for ext in ['png','svg']:fig.savefig(HERE/('neck_motion.'+ext),facecolor='#f6f8f8')
print('NECK_MOTION_PLOTS')
