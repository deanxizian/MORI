"""Draw source-based stage views and a clearly scoped assembly sequence."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'shell16_joint_feed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'projections.json').read_text())
rigid=json.loads((ORDER/'shell16_full_rigid_path/screen.json').read_text())
assert d['status']==rigid['status']=='PASS'
for report in [d,rigid]:
    for section in ['source_files','protected_sources']:
        for p,h in report[section].items():assert sha(ROOT/p)==h,p
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':11})
fig,ax=plt.subplots(figsize=(12.8,4.8),dpi=155);ax.set_axis_off()
fig.patch.set_facecolor('#f4f7f7')
fig.text(.045,.91,'装配顺序候选：零件路径已走通，完整线束仍待衔接',fontsize=18,color='#234149')
steps=[('1','外壳释放','倾斜16°，抬高14 mm','61个位置：含CAM线检查通过','#e0f1ea'),
       ('2','桥保持水平抬起','承重桥上移18 mm','37个位置：含CAM线检查通过','#e0f1ea'),
       ('3','一起后移','外壳与桥后移20 mm','81个位置：刚体检查通过','#e1edf5'),
       ('4','一起向上提离','桥累计抬高76.5 mm','118个位置：刚体检查通过','#e1edf5')]
for i,(number,title,move,result,colour) in enumerate(steps):
    x=.014+i*.25
    ax.add_patch(FancyBboxPatch((x,.34),.22,.43,boxstyle='round,pad=.008,rounding_size=.02',facecolor=colour,edgecolor='none',transform=ax.transAxes))
    ax.text(x+.016,.695,number,fontsize=22,color='#286679',transform=ax.transAxes)
    ax.text(x+.016,.585,title,fontsize=13.5,color='#203e46',transform=ax.transAxes)
    ax.text(x+.016,.495,move,fontsize=10.7,transform=ax.transAxes)
    ax.text(x+.016,.405,result,fontsize=9.3,color='#3f6269',transform=ax.transAxes)
    if i<3:ax.annotate('',xy=(x+.247,.56),xytext=(x+.225,.56),xycoords='axes fraction',arrowprops=dict(arrowstyle='->',color='#66838c'))
fig.text(.047,.245,'四段刚体复核：297个检查记录，294个不同位置；包含后板插头包络和14根固定身体线。',fontsize=11.4,color='#355760')
fig.text(.047,.162,'CAM导线目前只与前两段连通。后两段的导线调整、连续间隙、人手支承和其他线束仍未完成。',fontsize=11.2,color='#8c5c26')
fig.text(.047,.075,'使用既有未采用的结构候选，主模型M1.47未改。全部为名义几何检查，制造图尚未放行。',fontsize=10.6,color='#5a6d71')
fig.subplots_adjust(left=.03,right=.98,top=.86,bottom=.02)
fig.savefig(OUT/'sequence.png');plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(13.8,6.6),dpi=150)
colours={'Body_Upper':'#a3b9c2','Load_Frame':'#8a9a9d','Yaw_Base':'#3d7785',
         'MCU_Carrier':'#b5c4bc','Rear_Interface_PCB':'#197e61','Speaker':'#e4c493','Plug_rear_J2':'#d38336'}
labels=['原始位置','外壳16° / 抬高14 mm','桥再上抬18 mm']
for ax,scene,title in zip(axes,d['scenes'],labels):
    for name,polys in scene['projections']['YZ'].items():
        for poly in polys:
            p=np.asarray(poly)
            ax.fill(p[:,0],p[:,1],color=colours[name],alpha=.13 if name=='Body_Upper' else .32)
            pp=np.vstack([p,p[0]])
            ax.plot(pp[:,0],pp[:,1],color=colours[name],lw=1.2 if name=='Plug_rear_J2' else .65)
    for pin,pts in scene['curves'].items():
        p=np.asarray(pts);ax.plot(p[:,1],p[:,2],lw=1.,color=['#bd4c45','#9b5aab','#146d50','#5268b2'][int(pin)-1])
    ax.set_aspect('equal');ax.set_xlim(-93,93);ax.set_ylim(85,230)
    ax.grid(alpha=.15);ax.set_xlabel('Y / mm');ax.set_ylabel('Z / mm');ax.set_title(title,fontsize=12)
fig.suptitle('前两段：同一组CAM线与现有零件一起检查',fontsize=17,y=.96,color='#27434b')
fig.text(.055,.17,'橙色：后板J2插头包络　蓝绿色：承重桥　灰色：Load Frame　彩色细线：CAM导线',fontsize=11,color='#405e64')
fig.text(.055,.085,'图只显示身体附近，上方完整余线未画全。二维投影交叠不能当作三维相交；\n判定使用完整三维实体与导线间隙。插头外形保持原有保守包络。',fontsize=10.5,color='#66767b',linespacing=1.5)
fig.subplots_adjust(left=.045,right=.98,top=.86,bottom=.23,wspace=.27)
fig.savefig(OUT/'prefix_views.png');plt.close(fig)

outputs=['sequence.png','prefix_views.png']
report=dict(status='PASS',script_sha256=sha(SCRIPT),
    source_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'projections.json',ORDER/'shell16_full_rigid_path/screen.json']},
    outputs={n:sha(OUT/n) for n in outputs},main_applied=False,complete_attached_assembly='BLOCKED')
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SHELL16_PLOTS_SAVED')
