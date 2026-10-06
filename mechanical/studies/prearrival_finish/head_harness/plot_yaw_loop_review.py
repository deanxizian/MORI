"""Plot local yaw-loop evidence without presenting it as installed wiring."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
from matplotlib.patches import Circle
HERE=Path(__file__).resolve().parent
font=FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc');fontManager.addfont(font.get_file())
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})
seed=json.loads((HERE/'split_planar_loops_refined.json').read_text())
check=json.loads((HERE/'loop_source_solids.json').read_text())
assert check['status']=='PASS' and check['source_blend_sha256']==seed['source_blend_sha256']
selected=[g for g in seed['groups'] if g['status']=='PASS']
colors=['#ac681f','#2d6b86'];names=['供电＋喇叭：4 根','舵机上游：3 根']
fig=plt.figure(figsize=(14,9.2),dpi=160,facecolor='#f5f6f3')
grid=fig.add_gridspec(2,3,height_ratios=[1.3,1],left=.055,right=.97,bottom=.1,top=.80,hspace=.30,wspace=.22)
for i,yaw in enumerate([-60,0,60]):
    ax=fig.add_subplot(grid[0,i]);ax.set_facecolor('#fff')
    for j,g in enumerate(selected):
        pose=next(p for p in g['selected']['poses'] if p['yaw_deg']==yaw);p=np.asarray(pose['curve_mm'])
        ax.plot(p[:,0],p[:,1],color=colors[j],lw=2.8,label=names[j])
        ax.scatter(*p[0,:2],marker='s',s=52,color=colors[j],zorder=5,edgecolor='white',linewidth=.6)
        ax.scatter(*p[-1,:2],marker='o',s=60,color=colors[j],zorder=5,edgecolor='white',linewidth=.6)
    ax.scatter(0,0,s=16,color='#536066');ax.axhline(0,color='#dfe3e0',lw=.7);ax.axvline(0,color='#dfe3e0',lw=.7)
    ax.set(xlim=(-58,58),ylim=(-58,58),aspect='equal',xlabel='X / mm',ylabel='Y / mm' if i==0 else '')
    ax.set_title(f'Yaw {yaw:+d}°' if yaw else 'Yaw 0°',fontsize=14,pad=12)
    ax.spines[['top','right']].set_visible(False);ax.tick_params(colors='#627176',labelsize=9)

ax=fig.add_subplot(grid[1,0]);ax.set_facecolor('#fff')
for i,g in enumerate(selected):
    z=g['plane_z_mm'];r=g['diameter_mm']/2
    ax.add_patch(Circle((0,z),r,facecolor=colors[i],alpha=.85,edgecolor=colors[i]))
    ax.text(2.4,z,names[i]+f'\n直径占位 {2*r:.2f} mm',va='center',fontsize=10,color=colors[i])
a=selected[0]['plane_z_mm']+selected[0]['diameter_mm']/2
b=selected[1]['plane_z_mm']-selected[1]['diameter_mm']/2
ax.annotate('',xy=(-2.5,a),xytext=(-2.5,b),arrowprops=dict(arrowstyle='|-|',color='#475c66',lw=1.2))
ax.text(-3.4,(a+b)/2,f'{b-a:.3f} mm',ha='right',va='center',fontsize=10,color='#475c66')
ax.set(xlim=(-6.8,10.2),ylim=(148.7,158.1),aspect='equal',ylabel='Z / mm',xticks=[])
ax.set_title('两组占位的高度与间隙',fontsize=12,loc='left',pad=12)
ax.spines[['top','right','bottom']].set_visible(False)

ax=fig.add_subplot(grid[1,1:]);ax.axis('off')
notes=[('已通过的范围','#2d6b86',0.94),
       ('这两组环段：当前实体、已有 14 根固定线、130 个头部姿态。','#273b42',0.80),
       ('中心线环段长度约 261.0 / 340.1 mm；不是整根线的下料长度。','#273b42',0.67),
       ('仍未解决','#a25c22',0.47),
       ('UART 四根线：本次圆束、抬升与分层有限试算尚未通过。','#273b42',0.33),
       ('各端子到环段、环段到头部、俯仰段、真实固定点均未完成。','#273b42',0.20),
       ('圆束内每根线的长度变化、实际线径公差与往复寿命仍需核对。','#273b42',0.07)]
for msg,col,y in notes:ax.text(0,y,msg,fontsize=12 if y in [.94,.47] else 10.5,color=col,va='top',weight='bold' if y in [.94,.47] else 'normal')
fig.text(.055,.95,'头部转向线束：局部活动环试算',fontsize=22,color='#203239',weight='bold')
fig.text(.055,.90,'未选型导线占位；主模型未修改。此图仅为对应 7 根功能导线的两组占位环段，不代表完整跨关节线束。',fontsize=11,color='#52676d')
fig.text(.055,.855,'俯视投影　■ 身体侧暂定端点　● Yaw 侧暂定端点　两组处于不同高度；端点尚无实际固定结构。',fontsize=10,color='#52676d')
fig.text(.055,.032,'PROTOTYPE / UNVALIDATED　·　所有曲线均为 ASSUMED 规划占位；有限姿态几何通过不代表完整装配或耐久通过。',fontsize=10,color='#65757b')
for ext in ['png','svg']:fig.savefig(HERE/('yaw_loop_review.'+ext),facecolor=fig.get_facecolor())
plt.close(fig)
print('YAW_LOOP_REVIEW_PLOTTED')
