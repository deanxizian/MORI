"""Readable source-projection review of the CAM-first candidate and later ports."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'review';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
data=read(OUT/'projections.json');dense=read(BASE/'dense.json')
verification=read(BASE/'later_connections/grid_margin_approach/verification.json')
assert data['paths_sha256']==sha(ROOT/data['path_file'])==verification['paths_sha256']
assert all(r['full_0_3_margin_status']=='PASS' for r in verification['rows'])
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':10})
ink='#243d46';bg='#f5f8f8';green='#187e78';amber='#a86b1e'
fig,ax=plt.subplots(figsize=(11,7),dpi=145);fig.patch.set_facecolor(bg)
ax.set(xlim=(0,11),ylim=(0,7));ax.axis('off')
items=[
 ('先装 CAM 四线与承重桥','H03 两根线保留；H01 / H02 / H04 的 12 根线和 6 个插头后装。',green),
 ('按分步路径落入身体','四根 CAM 全长和共同 PH 插头均在场；408 个有限位置通过。',green),
 ('后装六个插头：路径已找到','离开最初 8 mm 插接段后，六条路径的连续扫掠保留 0.3 mm 名义余量。',green),
 ('接下来：带线装入、整理与固定','插头路径不能替代整束线装配；弯曲半径、供线长度和扎带仍要完成。',amber),
]
for i,(title,detail,color) in enumerate(items):
 y=5.8-i*1.3
 ax.add_patch(FancyBboxPatch((.3,y-.35),10.3,1,boxstyle='round,pad=.08',facecolor='white',edgecolor=color,lw=1.4))
 ax.text(.55,y+.26,str(i+1)+'  '+title,fontsize=15,color=ink,va='center')
 ax.text(.55,y-.13,detail,fontsize=10.5,color=color,va='center')
 if i<3:ax.annotate('',xy=(5.5,y-.63),xytext=(5.5,y-.45),arrowprops=dict(arrowstyle='->',color=ink,lw=1.4))
ax.text(.35,.22,'独立候选 · 主模型保持 M1.47\n采用未应用的颈部 / 头托研究几何；实物公差、手部工具和制造验证不在本图范围。',fontsize=11,color=ink)
fig.suptitle('CAM 线先装：解决一段顺序，继续补齐后装线束',fontsize=18,color=ink)
fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'order.png',facecolor=bg);plt.close(fig)

cols={'power_J17':'#de7c23','motion_J1':'#157aab','motion_J2':'#157aab','power_J13':'#de7c23','motion_J4':'#157aab','imu_J1':'#de7c23'}
parts={'Body_Upper':'#b7bfc3','Load_Frame':'#84979d','Yaw_Base':'#7fadaa','Power_Module':'#b7aa72','MCU_Carrier':'#88a085','Body_IMU':'#88a085','Battery':'#98aabd'}
fig,axs=plt.subplots(1,3,figsize=(16,7.6),dpi=145);fig.patch.set_facecolor(bg)
for ax,(name,plane,ports) in zip(axs,[('H01','YZ',['power_J17','motion_J1']),('H02','YZ',['motion_J2','power_J13']),('H04','XZ',['motion_J4','imu_J1'])]):
 dims=[1,2] if plane=='YZ' else [0,2]
 for part,color in parts.items():
  for poly in data['projections'][plane][part]:
   points=np.asarray(poly);points=np.vstack([points,points[0]])
   ax.plot(points[:,0],points[:,1],color=color,lw=.7,alpha=.75)
 for p in data['CAM_wire_centerlines_mm'].values():
  points=np.asarray(p);ax.plot(points[:,dims[0]],points[:,2],color='#b4a6a5',lw=.65,alpha=.8)
 for port in ports:
  points=np.asarray(data['ports'][port]['points_mm'])[:,dims]
  # Stored withdrawal order is reversed to depict installation from outside.
  points=points[::-1];color=cols[port]
  ax.plot(points[:,0],points[:,1],'-o',color=color,lw=2.4,ms=3,label=port)
  ax.plot(points[0,0],points[0,1],'s',color=color,ms=5)
  ax.plot(points[-1,0],points[-1,1],'*',color=color,ms=10)
  for i in range(len(points)-1):
   d=points[i+1]-points[i]
   if np.linalg.norm(d)>8:
    a=points[i]+.45*d;b=points[i]+.65*d
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.5,color=color))
 ax.set(xlim=(-85,100 if plane=='XZ' else 85),ylim=(90,218),aspect='equal',xlabel=('Y' if plane=='YZ' else 'X')+' / mm',ylabel='Z / mm',title=name+' · '+plane+' 投影')
 ax.grid(alpha=.15);ax.legend(loc='lower left',fontsize=9,framealpha=.95)
fig.suptitle('六个后装插头的接入路径：方块为外部起点，星号为插接终点',fontsize=17,color=ink)
fig.text(.055,.11,'浅色细线是当前阶段零件与 CAM 线的投影；二维交叉不等于三维相交。\n路径已按三维连续扫掠复核。其他插头全部保留在最终位置，H01 / H02 / H04 导线仍未放入此路径检查。',fontsize=11,color=ink)
fig.text(.055,.045,'0.3 mm 仅为研究中的名义余量，未计实物和制造公差。最初 8 mm 插接段仅检查名义外形；真实端子插合仍待厂家与实物确认。',fontsize=10.5,color=amber)
fig.tight_layout(rect=(0,.17,1,.94));fig.savefig(OUT/'connector_paths.png',facecolor=bg);plt.close(fig)
report=dict(status='PASS',scope='Source-based review images, not complete cable installation or manufacturing approval',
    script_sha256=sha(SCRIPT),projections_sha256=sha(OUT/'projections.json'),
    source_reports={str(p.relative_to(ROOT)):sha(p) for p in [BASE/'dense.json',BASE/'later_connections/grid_margin_approach/screen.json',BASE/'later_connections/grid_margin_approach/verification.json']},
    outputs={n:sha(OUT/n) for n in ['order.png','connector_paths.png']},main_applied=False)
(OUT/'plots.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_FIRST_PLOTS PASS')
