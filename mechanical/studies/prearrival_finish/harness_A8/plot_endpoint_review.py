"""Show finite graph reachability without disguising graph corners as wires."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,2,figsize=(13,7),dpi=155)
labels={'body':'下端：未找到身体出口','yaw':'上端：有折线通道，尚未满足弯曲要求'}
for ax,mode in zip(axes,['body','yaw']):
    d=json.loads((HERE/f'central_{mode}_escape_graph.json').read_text())
    data=np.load(HERE/d['reachable_nodes_file']);points=data['points_mm']
    rz=np.column_stack([np.linalg.norm(points[:,:2],axis=1),points[:,2]])
    rz=np.unique(np.round(rz,5),axis=0)
    ax.scatter(rz[:,0],rz[:,1],s=3,color='#83a8b2',alpha=.42,label='已连通且满足粗细间隙的图节点')
    start=d['root_mm'];ax.scatter([np.hypot(*start[:2])],[start[2]],s=70,color='#2f7560',zorder=4,label='研究起点')
    if d['path_mm']:
        path=np.asarray(d['path_mm']);r=np.linalg.norm(path[:,:2],axis=1)
        ax.plot(r,path[:,2],color='#b67c15',lw=1.6,marker='.',markersize=3,label='图上的折线路径（不是线材模型）')
    ax.axvline(30,color='#af5142',ls='--',lw=1.2)
    ax.set(xlim=(0,33),xlabel='距转轴半径 / mm',ylabel='Z / mm',title=labels[mode])
    if mode=='body':
        ax.axhline(136,color='#af5142',ls='--',lw=1.2)
        ax.set_ylim(134,161)
        ax.text(.04,.11,'目标：半径 ≥30 或 Z≤136\n在该有限图内未连通。',transform=ax.transAxes,fontsize=11,color='#934536',
                bbox=dict(facecolor='#f5f8f8',edgecolor='none',alpha=.95,pad=5))
    else:
        ax.axhline(204,color='#af5142',ls='--',lw=1.2)
        ax.set_ylim(179,205)
        ax.text(.46,.07,'线材弯曲、4根同时通过、\n固定与装入仍未完成。',transform=ax.transAxes,fontsize=11,color='#934536')
    ax.grid(alpha=.17);ax.legend(loc='upper left',fontsize=8,frameon=True)
fig.suptitle('现有中心间隙：上、下端分别核对，不能把局部通过当成整线完成',x=.06,ha='left',fontsize=17,y=.97)
fig.text(.06,.075,'已计入有限头部姿态的实体并集。图为“半径–高度”投影，各角度可能重叠，不能当作平面连续开口。',fontsize=10,color='#53666d')
fig.text(.06,.043,'搜索步长：径向0.4 mm、角度5°、高度0.5 mm；未找到路径不等于证明所有连续路线均不存在。',fontsize=10,color='#53666d')
fig.subplots_adjust(left=.075,right=.97,top=.84,bottom=.17,wspace=.23)
for ext in ['png','svg']:fig.savefig(HERE/f'endpoint_review.{ext}',facecolor='#f5f8f8')
plt.close(fig)
print('A8_ENDPOINT_REVIEW_SAVED')
