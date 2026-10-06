"""Explain J2's conditional transit result and its separate mating blockers."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch,Rectangle
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent;OUT=HERE/'terminal_threading';PROJECT=HERE.parents[3]
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
sections=json.loads((OUT/'sections.json').read_text())
route=json.loads((HERE/'joined_entry_screen.json').read_text())
transit=json.loads((OUT/'transit_screen.json').read_text())
selected=next(r for r in transit['results'] if r['status']=='PASS')
travel=np.asarray(selected['radial_z_tilt_rad'])
colors={'Yaw_Base':'#9ab1bb','Pitch_Yoke':'#a4bfb0','Yaw_Reaction_Link':'#c9a478','Yaw_Bearing':'#b7b6c2',
        'Yaw_Servo':'#e1cdb0','Pitch_Servo':'#e1cdb0'}
def fill(ax,polys,color,alpha=1):
    vertices=[];codes=[]
    for p in polys:
        if len(p)<3:continue
        vertices.extend(p+[p[0]]);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY])
    if vertices:ax.add_patch(PathPatch(PlotPath(vertices,codes),facecolor=color,edgecolor='#495c64',lw=.4,alpha=alpha))
fig,axes=plt.subplots(1,2,figsize=(12,7.8),dpi=155)
for ax,(name,xlim,ylim,label) in zip(axes,[('Yaw_Base',(3,22),(135,153),'身体侧入口'),('Pitch_Yoke',(3,23),(174,198),'头侧出口')]):
    layers=sections['45']
    for part,col in colors.items():fill(ax,layers[part],col)
    fill(ax,layers[name+'_removed'],'#db7770',.72)
    rec=next(r for r in route['rows'] if r['yaw_deg']==0 and r['azimuth_deg']==45)
    wire=np.array(rec['lower_curve_body_mm' if name=='Yaw_Base' else 'upper_curve_yaw_mm'])
    ax.plot(np.linalg.norm(wire[:,:2],axis=1),wire[:,2],color='#813e93',lw=2.0,label='装后导线中心线')
    ax.plot(travel[:,0],travel[:,1],color='#087f83',lw=1.8,linestyle='--',label='临时端子中心路线')
    candidates=np.where((travel[:,1]>ylim[0]+1)&(travel[:,1]<ylim[1]-1))[0]
    for i in candidates[np.linspace(0,len(candidates)-1,5).astype(int)]:
        r,z,tilt=travel[i];rotation=np.array([[math.cos(tilt),math.sin(tilt)],[-math.sin(tilt),math.cos(tilt)]])
        corners=np.array([[-.4,-1.95],[.4,-1.95],[.4,1.95],[-.4,1.95]])@rotation.T+[r,z]
        fill(ax,[corners.tolist()],'#138f90',.22)
    ax.set(xlim=xlim,ylim=ylim,aspect='equal',title=label,xlabel='45°径向距离 / mm',ylabel='Z / mm');ax.grid(alpha=.14)
fig.suptitle('J2 独立研究：装后线形与临时穿入路线分开检查',fontsize=16)
fig.legend([Patch(facecolor='#db7770'),plt.Line2D([],[],color='#813e93',lw=2),plt.Line2D([],[],color='#087f83',ls='--')],
           ['相对主模型的候选去除区','装后导线','裸端子临时路线'],loc='lower center',bbox_to_anchor=(.5,.07),ncol=3,fontsize=10)
fig.text(.06,.025,'裸端子采用原厂目录名义包络；加入对插插头后尚未整体通过。主模型未改，不能作为加工图。',fontsize=10.7)
fig.tight_layout(rect=[0,.18,1,.93]);fig.savefig(OUT/'transit_sections.png',facecolor='#f7f8f7');plt.close(fig)

mate=json.loads((PROJECT/'mechanical/studies/prearrival_preparation/mated_connector_review.json').read_text())
ports=json.loads((HERE/'h06_ports.json').read_text())
fig,ax=plt.subplots(figsize=(10,8),dpi=155)
for item in mate['rows']:
    if item['board']!='power':continue
    lo=np.array(item['bounds_mm'][:3]);hi=np.array(item['bounds_mm'][3:])
    if lo[2]<=139<=hi[2]:
        problematic=item['ref'] in ['J11','J4','J12']
        ax.add_patch(Rectangle(lo[:2],*(hi-lo)[:2],facecolor='#f5d2bb' if problematic else '#e5e9eb',edgecolor='#a56343' if problematic else '#7e8d94',lw=1))
        ax.text(*(lo[:2]+hi[:2])/2,item['ref'],ha='center',va='center',fontsize=9)
for phase,col in zip([45,135,225,315],['#b53047','#397dab','#967729','#378373']):
    a=math.radians(phase);rad=np.array([math.cos(a),math.sin(a)])
    ray=np.array([14.8*rad,32*rad]);ax.plot(ray[:,0],ray[:,1],color=col,lw=2.5)
    ax.scatter(*ray[-1],color=col,s=34);ax.scatter(*ray[0],facecolor='white',edgecolor=col,s=30,zorder=3)
    ax.text(*(ray[-1]+[0,-3.]),f'{phase}°',ha='center',va='center',color=col,fontsize=11)
for pin,p in ports['body']['pins'].items():ax.scatter(*p[:2],s=28,color='#293e55');ax.text(p[0],p[1]-2.2,pin,ha='center',fontsize=8)
ax.text(18.5,-51,'Motion J5：4 个编号引出位置\n高度 Z=130.64 mm（出线面为分配值）',ha='center',fontsize=9)
ax.set(xlim=(-43,43),ylim=(-56,38),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
ax.grid(alpha=.13);ax.set_title('接到板卡前，还必须避开对插插头的空间',fontsize=16,pad=15)
fig.text(.10,.025,'俯视：Z=139 mm 的胶壳预留包络。彩线为 J1 原径向引出段；空心点为内收入口研究点。\n胶壳采用保守包络，插合深度仍待核实；当前发现的是模型/分配冲突，不宣称实物必然干涉。',fontsize=10)
fig.tight_layout(rect=[0,.10,1,1]);fig.savefig(OUT/'body_mating_review.png',facecolor='#f7f8f7');plt.close(fig)
print('J2_PLOTS_SAVED')
