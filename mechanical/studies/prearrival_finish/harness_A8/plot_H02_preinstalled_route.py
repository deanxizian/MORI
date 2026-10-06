"""Plot source-derived H02 curves, with legacy curves explicitly identified."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'H02_preinstalled';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
screen=read(OUT/'screen.json');check=read(OUT/'verification.json')
assert check['status']=='PASS' and check['screen_sha256']==sha(OUT/'screen.json')
current=screen['selected']['routes'];prior=read(A8.parent/'harness_A2/ecowire_joint.json')['routes']
proj=read(BASE/'review/projections.json')
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':11})
fig,axs=plt.subplots(1,2,figsize=(12.5,6.8),dpi=160);fig.patch.set_facecolor('#f4f7f7')
colors={'H02_1':'#127c71','H02_2':'#2765aa'}
for ax,plane,axis in zip(axs,['XZ','YZ'],[0,1]):
    for part in ['MCU_Carrier','Power_Module','Yaw_Base']:
        for poly in proj['projections'][plane][part]:
            p=np.asarray(poly);p=np.vstack([p,p[0]])
            ax.plot(p[:,0],p[:,1],color='#adb6ba',lw=.65,alpha=.65)
    for i,row in enumerate([r for r in prior if r['harness']=='H02']):
        p=np.asarray(row['curve_mm'])
        ax.plot(p[:,axis],p[:,2],'--',lw=1.6,color='#868487',label='原 H02 走向' if i==0 else None)
    for row in current:
        p=np.asarray(row['curve_mm'])
        ax.plot(p[:,axis],p[:,2],lw=2.6,color=colors[row['id']],label=row['id']+' 新候选')
        ax.scatter(p[[0,-1],axis],p[[0,-1],2],s=24,color=colors[row['id']],marker='s',zorder=6)
    for i,p in enumerate(proj['CAM_wire_centerlines_mm'].values()):
        p=np.array(p)
        ax.plot(p[:,axis],p[:,2],color='#cb783f',lw=1,alpha=.8,label='CAM 零位线形' if i==0 else None)
    ax.set_xlim((10,42) if plane=='XZ' else (-36,3))
    ax.set_ylim(126,150);ax.set_aspect('equal')
    ax.set_xlabel(plane[0]+' / mm');ax.set_ylabel('Z / mm')
    ax.set_title(plane+' 投影 · 插头出口位置保持')
    ax.grid(alpha=.15);ax.legend(loc='upper left',fontsize=9,framealpha=.95)
fig.suptitle('H02 改为提前接好：降低中段，避开 CAM 随桥装入的区域',fontsize=18,color='#203e47')
fig.text(.065,.145,'两根线分别保留原针序、端点和 5 mm 端后直段；圆弯半径仍为 5.08 mm。\n408 个身体装配位置、130 个头部姿态通过；二维重叠不表示三维相交。',fontsize=12,color='#203e47')
fig.text(.065,.055,'独立研究候选，未修改主模型。线材与端子出口未最终选定；名义路径约 50.40 / 53.98 mm，不能用于裁线。\n其他跨关节线、H01 / H04 带线后装、人手操作与固定仍需完成。',fontsize=10.5,color='#97601a')
fig.tight_layout(rect=(0,.29,1,.93));fig.savefig(OUT/'comparison.png');plt.close(fig)
report=dict(status='PASS',script_sha256=sha(SCRIPT),scope='Source curve comparison only',
    source_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'screen.json',OUT/'verification.json',BASE/'review/projections.json',A8.parent/'harness_A2/ecowire_joint.json']},
    outputs={'comparison.png':sha(OUT/'comparison.png')},main_applied=False)
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('H02_COMPARISON_SAVED')
