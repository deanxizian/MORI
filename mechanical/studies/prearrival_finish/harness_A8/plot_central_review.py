"""Source-backed local passage views; visibly separate unresolved end routes."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
HERE=Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
curves=json.loads((HERE/'central_uart_curves.json').read_text())
checks=json.loads((HERE/'central_uart_source_check.json').read_text())
sec_path=HERE.parent/'head_harness/neck_sections.json';sections=json.loads(sec_path.read_text())
assert curves['source_blend_sha256']==sections['source_blend_sha256']==checks['source_blend_sha256']
colors=['#b87814','#d79b2e','#9a690c','#dca35e']
fig=plt.figure(figsize=(14,8),dpi=150)
gs=fig.add_gridspec(2,4,width_ratios=[1.35,1,1,1],height_ratios=[1,.45])
ax=fig.add_subplot(gs[:,0])
palette={'body':'#c7d4db','yaw':'#73a8a7','pitch':'#dbbd9b'}
def compound(polygons):
    vs=[];codes=[]
    for p in polygons:
        if len(p)<3:continue
        vs+=p+[p[0]];codes += [MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY]
    return MPath(vs,codes)
for name,layer in sections['side_section']['layers'].items():
    ax.add_patch(PathPatch(compound(layer['polygons_mm']),facecolor=palette.get(layer['group'],'#bbc4c8'),edgecolor='#556a70',lw=.45))
for x in [-6.8,6.8]:
    ax.plot([x,x],[150,182],color='#bc861b',lw=3,label='已检查的中间段' if x>0 else None)
    ax.plot([x,x],[148,150],color='#bc861b',lw=1.2,ls=':')
    ax.plot([x,x],[182,188],color='#bc861b',lw=1.2,ls=':')
ax.annotate('下端直行受限',xy=(-6.8,148),xytext=(-17,139),arrowprops={'arrowstyle':'->','color':'#ae4d39'},color='#ae4d39',fontsize=10)
ax.annotate('上端直行受限',xy=(6.8,188),xytext=(-15,201),arrowprops={'arrowstyle':'->','color':'#ae4d39'},color='#ae4d39',fontsize=10)
ax.set(xlim=(-18,18),ylim=(135,205),aspect='equal',xlabel='Y / mm',ylabel='Z / mm',title='现有实体剖面 · X = 0')
ax.grid(alpha=.13)
for col,yaw in enumerate([-60,0,60],1):
    a=fig.add_subplot(gs[0,col],projection='3d')
    pose=next(p for p in curves['selected']['poses'] if p['yaw_deg']==yaw)
    pts=np.asarray(pose['first_wire_curve_mm'])
    th=np.linspace(0,2*np.pi,101)
    a.plot(6*np.cos(th),6*np.sin(th),np.full(len(th),150),color='#9caaaf',lw=.7)
    a.plot(6*np.cos(th),6*np.sin(th),np.full(len(th),182),color='#9caaaf',lw=.7)
    for i,phi in enumerate(curves['wire_zero_azimuths_deg']):
        r=math.radians(phi);rot=np.array([[np.cos(r),-np.sin(r),0],[np.sin(r),np.cos(r),0],[0,0,1.]])
        p=pts@rot.T;a.plot(*p.T,color=colors[i],lw=2.2)
        a.scatter(*p[[0,-1]].T,color=colors[i],s=13)
    a.set(xlim=(-8,8),ylim=(-8,8),zlim=(148,184),title=f'Yaw {yaw:+d}°')
    a.set_box_aspect((16,16,36));a.view_init(elev=20,azim=-55)
    a.set(xticks=[-6,0,6],yticks=[-6,0,6],zticks=[150,166,182])
    a.set_xlabel('X');a.set_ylabel('Y');a.set_zlabel('Z')
    a.tick_params(labelsize=8)
note=fig.add_subplot(gs[1,1:]);note.axis('off')
minbend=min(p['sampled_minimum_bend_radius_mm'] for p in curves['selected']['poses'])
text=(f"局部段：4 根 × 33.2 mm；最大外径 0.6604 mm；最小抽样弯曲半径 {minbend:.2f} mm。\n"
      "130 个头部组合姿态：当前实体、已查的两组外圈及 14 根固定线未检出碰撞。\n"
      "上下端直接延长会遇到实体，侧向进出、固定点、俯仰段和完整线长仍未解决。\n\n"
      "黄色为 PLACEHOLDER / ASSUMED 路线。点是研究端点，不是已设计的固定座；\n"
      "33.2 mm 只是中间段几何长度，不可作为供应商下料长度。主模型保持 M1.47。")
note.text(0,1,text,va='top',fontsize=11,linespacing=1.9,color='#344d56')
fig.suptitle('A8 细线候选：中心间隙能容纳局部运动，完整进出线还未闭合',x=.055,ha='left',fontsize=18,y=.97)
fig.subplots_adjust(left=.065,right=.98,top=.87,bottom=.08,wspace=.3,hspace=.2)
for ext in ['png','svg']:fig.savefig(HERE/('central_uart_review.'+ext),facecolor='#f5f8f8')
plt.close(fig)
print('A8_CENTRAL_REVIEW_SAVED')
