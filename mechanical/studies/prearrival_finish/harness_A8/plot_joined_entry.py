"""Source-section diagrams for the unapproved coherent J1 wire study."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent;OUT=HERE/'joined_entry_candidate'
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
sections=json.loads((OUT/'sections.json').read_text());route=json.loads((HERE/'joined_entry_screen.json').read_text())
check=json.loads((OUT/'screening.json').read_text())
colors={'Yaw_Base':'#7a9aa9','Pitch_Yoke':'#96b4a7','Yaw_Reaction_Link':'#bf925c','Yaw_Bearing':'#a1a5b4',
        'Yaw_Servo':'#d9c6ac','Pitch_Servo':'#ddc8ac'}
def fill(ax,polys,color,alpha=1):
    vs=[];codes=[]
    for p in polys:
        if len(p)<3:continue
        vs.extend(p+[p[0]]);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY])
    if vs:ax.add_patch(PathPatch(PlotPath(vs,codes),facecolor=color,edgecolor='#34434a',lw=.5,alpha=alpha))
fig,axes=plt.subplots(2,2,figsize=(13,10),dpi=145)
for row,(part,xlim,ylim,title) in enumerate([
    ('Yaw_Base',(3,18),(136,151),'下端入口'),('Pitch_Yoke',(3,20),(176,199),'上端出口')]):
    for col,state in enumerate(['baseline','candidate']):
        ax=axes[row,col];layers=sections['45']
        for name,color in colors.items():
            key=name+'_baseline' if state=='baseline' and name in ['Yaw_Base','Pitch_Yoke'] else name
            fill(ax,layers[key],color)
        fill(ax,layers[part+'_removed'],'#e5756b',.7)
        # At zero yaw the two approach pieces stay in the45deg radial plane;
        # the central slack curve is deliberately omitted from this section.
        rec=next(r for r in route['rows'] if r['yaw_deg']==0 and r['azimuth_deg']==45)
        p=np.array(rec['lower_curve_body_mm' if row==0 else 'upper_curve_yaw_mm'])
        rr=np.linalg.norm(p[:,:2],axis=1)
        ax.plot(rr,p[:,2],color='#842c8c',lw=1.8,label='导线中心线')
        ax.set(xlim=xlim,ylim=ylim,aspect='equal',title=f'{title} · '+('当前模型' if state=='baseline' else 'J1独立候选'),
               xlabel='45°径向距离 / mm',ylabel='Z / mm')
        ax.grid(alpha=.14)
fig.legend([Patch(facecolor=c) for c in colors.values()]+[Patch(facecolor='#e5756b')],
           list(colors)+['候选去除体'],loc='lower center',ncol=4,fontsize=9)
fig.suptitle('四根 UART 导线的连续进出路线 · 主模型未修改',fontsize=16)
fig.text(.075,.073,'仅两处打印件局部开通；弯曲R8，孔道名义Ø1.56。固定、装入、承压与薄边仍需检查。',fontsize=11)
fig.tight_layout(rect=[0,.12,1,.94]);fig.savefig(OUT/'sections_review.png',facecolor='#f7f8f7');plt.close(fig)

fig=plt.figure(figsize=(15,6.6),dpi=145)
for i,yaw in enumerate([-60,0,60]):
    ax=fig.add_subplot(1,3,i+1,projection='3d')
    for rec,color in zip([r for r in route['rows'] if r['yaw_deg']==yaw],['#b53047','#367eb7','#c18b29','#519476']):
        p=np.array(rec['curve_mm']);ax.plot(p[:,0],p[:,1],p[:,2],color=color,lw=1.6)
        ax.scatter(*p[0],color=color,s=12);ax.scatter(*p[-1],color=color,s=12)
    ax.set(xlim=(-34,34),ylim=(-34,34),zlim=(136,208),title=f'Yaw {yaw:+d}°',xlabel='X/mm',ylabel='Y/mm',zlabel='Z/mm')
    ax.set_box_aspect((1,1,1.1));ax.view_init(elev=18,azim=-62)
fig.suptitle('同一套端点与切线连接：下端固定，中央变形，上端随Yaw转动',fontsize=16)
fig.text(.05,.075,f'每根局部几何长度 {route["analytic_staging_length_mm"]:.3f} mm；两端仍是研究位置，没有接到板卡。不能作下料长度。',fontsize=11)
fig.tight_layout(rect=[0,.12,1,.93]);fig.savefig(OUT/'three_pose_paths.png',facecolor='#f7f8f7');plt.close(fig)
print('J1_PLOTS_SAVED',check['status'])
