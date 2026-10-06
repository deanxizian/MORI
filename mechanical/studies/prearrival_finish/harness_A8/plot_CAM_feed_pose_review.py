"""Plot saved configurations as separate poses, never as an assembly sequence."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/feed_pose_packing'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
projection=json.loads((OUT/'projections.json').read_text())
assert projection['status']=='PASS'
for p,digest in projection['source_files'].items():assert sha(ROOT/p)==digest
for p,digest in projection['protected_sources'].items():assert sha(ROOT/p)==digest
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':11})
fig,axes=plt.subplots(2,3,figsize=(15.5,10.6),dpi=155)
fig.patch.set_facecolor('#f5f7f8')
colours=['#ce5a36','#207ab8','#078773','#9160ad']
labels=[('source','坐稳基准'),('lift18','桥上移 18 mm：独立排布'),('rear14_lift18','再后移 14 mm：独立排布')]
for col,(key,title) in enumerate(labels):
    view=projection['views'][key]
    for row,(plane,axis) in enumerate([('XZ',0),('YZ',1)]):
        ax=axes[row,col]
        for name,polys in view['projections'][plane].items():
            for poly in polys:
                points=np.asarray(poly);points=np.vstack([points,points[0]])
                if name=='Body_Upper':
                    ax.plot(points[:,0],points[:,1],color='#bac1c5',lw=.6,linestyle='--',alpha=.6)
                else:
                    ax.fill(points[:,0],points[:,1],color='#dde3e5',alpha=.30)
                    ax.plot(points[:,0],points[:,1],color='#a6b3b8',lw=.65,alpha=.8)
        for name,polys in projection['body_projections'][plane].items():
            for poly in polys:
                points=np.asarray(poly)
                ax.fill(points[:,0],points[:,1],color='#7f8a8f',alpha=.42)
        for pin,points in view['curves'].items():
            p=np.asarray(points);colour=colours[int(pin)-1]
            ax.plot(p[:,axis],p[:,2],color=colour,lw=1.8,alpha=.98)
            ax.scatter(p[0,axis],p[0,2],color=colour,s=14,marker='s',zorder=7)
        ax.set_xlim(-83,83);ax.set_ylim(120,236);ax.set_aspect('equal')
        ax.grid(alpha=.13);ax.set_xlabel(plane[0]+' / mm');ax.set_ylabel('Z / mm')
        ax.set_title((title if row==0 else '对应侧面投影')+' · '+plane,fontsize=12.5,pad=10)
        ax.set_facecolor('#fff')
handles=[Line2D([0],[0],color=c,lw=2,label='CAM '+str(i+1)) for i,c in enumerate(colours)]
handles.append(Line2D([0],[0],color='#8c999e',lw=4,label='已有身体线束（含低位 H02）'))
fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.93),ncol=5,frameon=False,fontsize=11)
fig.suptitle('CAM 分段送线：两个中间位置放得下，连接它们的动作仍未通过',fontsize=19,color='#263e48',y=.984)
fig.text(.055,.091,'三个位置分别显示，不能当作装配动作的连续画面。模型使用独立候选打印件；主模型 M1.47 未修改。',fontsize=11.5,color='#684c23')
fig.text(.055,.036,'计算保留完整线长；图中仅展示身体附近，上方竖直暂存余线被画框截去。二维投影重叠不等于三维相交。\n两处检查保留 14 根身体线和 29 个插头空间；端子仍是尺寸分配，连续送线、人手操作及完整线束尚未验证。',fontsize=10.5,color='#58666e',linespacing=1.65)
fig.subplots_adjust(left=.045,right=.985,bottom=.14,top=.87,hspace=.24,wspace=.2)
fig.savefig(OUT/'comparison.png');plt.close(fig)
record=dict(status='PASS',scope='Source-based configuration comparison, not installation validation',
            script_sha256=sha(SCRIPT),source_files={str((OUT/'projections.json').relative_to(ROOT)):sha(OUT/'projections.json')},
            outputs={'comparison.png':sha(OUT/'comparison.png')},main_applied=False,whole_harness='BLOCKED')
(OUT/'plot.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('CAM_FEED_POSE_PLOT_SAVED')
