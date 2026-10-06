"""Plot actual source sections, complete wire allocations and staged order."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,PathPatch,Patch
from matplotlib.path import Path as PlotPath
from matplotlib import font_manager
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
FULL=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head'
OUT=FULL/'split_assembly/review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
sec=read(OUT/'sections.json');stock=read(FULL/'bridge_wire_stock/screen.json')
split=read(FULL/'split_assembly/screen.json');diag=read(FULL/'split_assembly/pitch_stages/interface_contacts/diagnosis.json')
assert sec['script_sha256']==sha(A8/'extract_CAM_staged_supply_sections.py')
assert all(r['status']=='PASS' for r in diag['order_rows'])
assert sha(ROOT/sec['complete_wire_arrays_path'])==sec['complete_wire_arrays_sha256']
arr=np.load(ROOT/sec['complete_wire_arrays_path'])
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':11})
bg='#f6f8f8';ink='#213b43';green='#167e79';amber='#b07122';red='#c23f37'
def fill(ax,polys,col,edge=None,alpha=1):
    vv=[];codes=[]
    for p in polys:
        if len(p)<3:continue
        vv+=p+[p[0]];codes += [PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY]
    if vv:ax.add_patch(PathPatch(PlotPath(vv,codes),facecolor=col,edgecolor=edge or col,lw=.8,alpha=alpha))
def outline(ax,polys,col,lw=.8):
    for p in polys:
        q=np.vstack([p,p[0]]);ax.plot(q[:,0],q[:,1],color=col,lw=lw)
fig,ax=plt.subplots(figsize=(10,6.5),dpi=140);fig.patch.set_facecolor(bg)
ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
items=[
 ('1  身体上壳与固定承重桥','头部组件尚未安装；旧分步路径的 408 个有限位置通过'),
 ('2  偏航组件＋输出件＋舵盘','共 22 件，从上方装入；181 个有限位置通过'),
 ('3  头托＋CAM 总成','共 14 件，从上方装入；141 个有限位置通过'),
 ('4  两侧短轴、光学框架、外壳','短轴后装；相机支架与前壳的小相交仍待处理'),
]
for i,(title,desc) in enumerate(items):
    y=4.8-i*1.17;col=green if i<3 else amber
    ax.add_patch(FancyBboxPatch((.3,y-.42),9.3,.92,boxstyle='round,pad=.08',fc='white',ec=col,lw=1.3))
    ax.text(.6,y+.18,title,color=ink,fontsize=14,va='center')
    ax.text(.6,y-.17,desc,color=col,fontsize=10.5,va='center')
    if i<3:ax.annotate('',xy=(5,y-.66),xytext=(5,y-.5),arrowprops=dict(arrowstyle='->',color=ink,lw=1.5))
ax.text(.3,.15,'这是无完整线束的名义刚体顺序候选。舵盘与短轴仍待厂家资料，\n紧固工具、反力夹初装、完整供线及连续装入尚未闭合；未改主模型或主动画。',color=ink,fontsize=11)
fig.suptitle('装配顺序补查：把先装、后装的零件说清楚',fontsize=16,color=ink)
fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'assembly_order.png',facecolor=bg);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.3,8),dpi=140)
for n,col in [('Body_Upper','#adb7bb'),('Load_Frame','#839296'),('Yaw_Base','#7fadae'),('Power_Module','#9d914c'),('MCU_Carrier','#839b80')]:
    outline(ax,sec['YZ_projections'][n],col)
cols=['#008c95','#c58930','#5b6daf','#ad567c']
for pin,col in zip(range(1,5),cols):
    p=arr['pin'+str(pin)];ax.plot(p[:,1],p[:,2],color=col,lw=1.3,label='几何槽位 '+str(pin))
    ax.plot(p[-1,1],p[-1,2],'o',color=col,ms=3)
ax.axhline(193,color='#617178',ls='--',lw=.8)
ax.text(20,275,'完整线长已纳入\n头部上方临时竖直存放\n153–162 mm / 根',fontsize=11,color=ink)
ax.text(18,187,'Z193 临时分界',fontsize=10,color=ink)
ax.annotate('共同 PH 插头\n与基板插接处',xy=(-45,127),xytext=(-76,93),arrowprops=dict(arrowstyle='->',color=ink),fontsize=10,color=ink)
ax.set(xlim=(-90,95),ylim=(82,370),aspect='equal',xlabel='Y / mm',ylabel='Z / mm')
ax.grid(alpha=.15);ax.legend(loc='upper left',fontsize=9)
fig.suptitle('四根 CAM 线：全长候选侧向投影',fontsize=15,color=ink)
fig.text(.09,.025,'实线为名义全长中心线，细灰线为零件投影轮廓。\n投影会重叠；不是剖面、裁线图或已通过的装配路线。',fontsize=10,color=ink)
fig.tight_layout(rect=(0,.08,1,.95));fig.savefig(OUT/'wire_stock.png',facecolor=bg);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11.6,5.6),dpi=145)
for ax,key,part,limits,title in [
 (axs[0],'camera_support_X6','Display_Frame',((26.7,27.4),(272.1,272.8)),'相机支架上角'),
]:
    r=sec['sections'][key];p=r['polygons']
    fill(ax,p['Head_Front'],'#c9d2d5');fill(ax,p[part],'#8ab0b3',alpha=.8)
    fill(ax,p['overlap'],'#ef6e54')
    for n in ('Head_Front',part):outline(ax,p[n],'#526b70',.7)
    plane=r['plane'];value=r['coordinate_mm']
    ax.set(xlim=limits[0],ylim=limits[1],aspect='equal',xlabel=('Y' if plane=='X' else 'X')+' / mm',ylabel=('Z' if plane=='X' else 'Y')+' / mm',title=f'{title}\n{plane} = {value:.4f} mm')
    ax.grid(alpha=.16)
lcd=sec['sections']['LCD_rim_Z237_4']
assert lcd['intersection_mm3']<1e-9
axs[1].axis('off')
axs[1].text(.08,.85,'LCD 原相交已排除',fontsize=16,color=green)
axs[1].text(.08,.69,'隐藏碰撞代理未同步到当前姿态，\n此前产生约 0.148 mm³ 相交误报。',fontsize=12,color=ink,linespacing=1.7)
axs[1].text(.08,.47,'刷新检查姿态后：\n名义相交为 0 mm³，该处不改零件。',fontsize=12,color=green,linespacing=1.7)
axs[1].text(.08,.19,'这仍使用两处接插件的保守碰撞包络，\n不能代替完整实物配合验证。',fontsize=11,color=ink,linespacing=1.7)
fig.suptitle('相机支架小相交与屏幕误报复核',fontsize=16,color=ink)
fig.legend([Patch(fc='#c9d2d5'),Patch(fc='#8ab0b3'),Patch(fc='#ef6e54')],['头前壳','光学零件/支架','名义相交'],loc='lower center',bbox_to_anchor=(.5,.1),ncol=3)
fig.text(.07,.035,'相机支架与前壳名义相交体积约 0.00765 mm³；这是 CAD 诊断，不是实测过盈。\n主模型保持；后续需处理该处局部间隙、核对壳厚和安装路径。',fontsize=10,color=ink)
fig.tight_layout(rect=(0,.2,1,.93));fig.savefig(OUT/'contact_sections.png',facecolor=bg);plt.close(fig)
report=dict(status='PASS',scope='Source-derived nominal diagnostic images, not assembly approval',script_sha256=sha(SCRIPT),
 source_main_sha256=sec['source_main_sha256'],sections_sha256=sha(OUT/'sections.json'),
 source_reports={str(p.relative_to(ROOT)):sha(p) for p in [FULL/'bridge_wire_stock/screen.json',FULL/'split_assembly/screen.json',FULL/'split_assembly/pitch_stages/interface_contacts/diagnosis.json']},
 outputs={n:sha(OUT/n) for n in ['assembly_order.png','wire_stock.png','contact_sections.png']},main_applied=False)
(OUT/'plots.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('STAGED_SUPPLY_PLOTS PASS')
