"""Render the located wire-pair problems from saved 3D curve samples."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'shell16_packing_diagnosis'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'diagnosis.json').read_text())
assert sha(A8/'diagnose_shell16_wire_packing.py')==d['script_sha256']
assert sha(OUT/'curves.npz')==d['curves_sha256']
data=np.load(OUT/'curves.npz')
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':10})
fig,axs=plt.subplots(2,3,figsize=(12.5,8.),dpi=150)
colors={1:'#b7553b',2:'#3b699f',3:'#187565',4:'#8954a0'}
titles=['颈部：CAM2 下移靠近 CAM1 上升段','出线口：CAM3 转弯靠近 CAM4']
for row,case_index in enumerate([0,2]):
    case=d['diagnoses'][case_index];pins=[case['failure']['a'],case['failure']['b']]
    close=np.asarray(case['closest']['positions_mm']);center=close.mean(0)
    for col,(a,b,name) in enumerate([(0,1,'俯视 XY'),(0,2,'正视 XZ'),(1,2,'侧视 YZ')]):
        ax=axs[row,col]
        for pin in pins:
            p=data[f'case{case_index}_pin{pin}']
            # Keep lines in this local 3D region, not remote crossing projections.
            visible=np.all(np.abs(p-center)<6.,axis=1)
            pp=p.copy();pp[~visible]=np.nan
            ax.plot(pp[:,a],pp[:,b],lw=2,color=colors[pin],label=f'CAM{pin}')
        ax.plot(close[:,a],close[:,b],'o--',lw=1,color='#bc3244',ms=4)
        ax.set_aspect('equal');ax.set_xlim(center[a]-5,center[a]+5);ax.set_ylim(center[b]-5,center[b]+5)
        ax.grid(alpha=.16);ax.set_xlabel('XYZ'[a]+' / mm');ax.set_ylabel('XYZ'[b]+' / mm')
        ax.set_title(name);ax.legend(loc='lower right',fontsize=9)
    fig.text(.047,.88-row*.4,titles[row]+f"；保守表面间隙 {case['failure']['surface_gap_lower_bound_mm']:.3f} mm",fontsize=12,color='#274b57')
fig.suptitle('共同后移的两个局部间隙问题',fontsize=17,y=.98,color='#27434b')
fig.text(.047,.055,'彩线为导线中心线，红点为采样最近点。图中线宽不表示真实直径；三维计算采用外径0.6604 mm。',fontsize=10,color='#536770')
fig.text(.047,.023,'目标间隙0.3 mm。低于目标不一概等同实体相交；本图展示诊断，不是已采用的装配方案。',fontsize=10,color='#536770')
fig.subplots_adjust(left=.06,right=.98,top=.825,bottom=.17,hspace=.65,wspace=.29)
fig.savefig(OUT/'local_pairs.png');plt.close(fig)
report=dict(status='PASS',scope='Source-based local curve illustration',script_sha256=sha(SCRIPT),
            source_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'diagnosis.json',OUT/'curves.npz']},
            outputs={'local_pairs.png':sha(OUT/'local_pairs.png')},main_applied=False)
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LOCAL_PAIR_PLOT_SAVED')
