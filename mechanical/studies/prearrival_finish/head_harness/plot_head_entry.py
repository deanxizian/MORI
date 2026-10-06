"""Review the independent clearance-graph paths without depicting them as cables."""
from pathlib import Path
import json, hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'head_entry_shortest.json').read_text())
assert d['status']=='PASS'
font=FontProperties(fname='/System/Library/Fonts/STHeiti Light.ttc')
font_manager.fontManager.addfont(font.get_file())
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})
names={'CAM_POWER_AND_SPK':'供电／喇叭','SERVO':'舵机','UART':'UART'}
colors=['#176b80','#b57528','#41806a']
fig=plt.figure(figsize=(12,7.6),dpi=160,facecolor='#f7f8f7')
ax=fig.add_subplot(121,projection='3d')
side=fig.add_subplot(122)
for row,color in zip(d['groups'],colors):
    p=np.array(row['path_mm'])
    label=f"{names[row['id']]}：Ø{row['planning_diameter_mm']:.3f} mm"
    ax.plot(*p.T,color=color,lw=2.4,label=label)
    ax.scatter(*p[[0,-1]].T,color=color,s=25)
    side.plot(p[:,1],p[:,2],color=color,lw=2.4,label=label)
    side.scatter(p[[0,-1],1],p[[0,-1],2],color=color,s=25)
ax.set(xlabel='X / mm',ylabel='Y / mm',zlabel='Z / mm',xlim=(10,48),ylim=(-5,35),zlim=(155,205))
ax.set_box_aspect((38,40,50));ax.view_init(elev=20,azim=-55)
ax.set_title('Yaw 坐标中的独立通道折线',pad=20)
side.set(xlabel='Y / mm',ylabel='Z / mm',ylim=(155,205),xlim=(-1,36))
side.set_title('侧向投影：三条路径靠近并部分重叠',pad=20)
side.grid(alpha=.15);side.spines[['top','right']].set_visible(False)
side.legend(loc='lower right',fontsize=10,framealpha=.95)
fig.suptitle('可以找到通道；还不是可装配的线束',x=.06,y=.97,ha='left',fontsize=19)
fig.text(.06,.12,'各自的名义表面间隙下界：供电／喇叭 0.347 mm；舵机 0.322 mm；UART 0.329 mm。',fontsize=11,color='#344d57')
fig.text(.06,.077,'点是研究起止位置，不是插头。折线含尖角；未证明三束同时容纳、允许弯曲半径或夹持方案。',fontsize=11,color='#895623')
fig.text(.06,.038,'源实体按 13 个 Yaw × 10 个 Pitch 姿态检查；本图隐藏实体以便比较路线，主模型未修改。',fontsize=10,color='#59676c')
fig.subplots_adjust(left=.04,right=.95,bottom=.21,top=.85,wspace=.18)
for ext in ['png','svg']:fig.savefig(HERE/('head_entry_review.'+ext),facecolor=fig.get_facecolor())
plt.close(fig)
print('HEAD_ENTRY_PLOT',hashlib.sha256((HERE/'head_entry_shortest.json').read_bytes()).hexdigest())
