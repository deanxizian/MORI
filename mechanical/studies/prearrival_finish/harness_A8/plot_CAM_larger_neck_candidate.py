"""Plot verified sections of the independent larger-contact neck candidate."""
from pathlib import Path
import hashlib,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch
from matplotlib import font_manager
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
check=json.loads((OUT/'verification.json').read_text());assert check['status']=='PASS'
assert check['verified_sections_sha256']==sha(OUT/'verified_sections.json')
sec=json.loads((OUT/'verified_sections.json').read_text())
path=np.load(OUT/'lower_bend/selected_path.npz')['radial_z_axis_angle']
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False})
def fill(ax,polys,color,edge='#55616b',alpha=1):
    vv=[];codes=[]
    for poly in polys:
        if len(poly)<3:continue
        vv+=poly+[poly[0]];codes += [PlotPath.MOVETO]+[PlotPath.LINETO]*(len(poly)-1)+[PlotPath.CLOSEPOLY]
    if vv:ax.add_patch(PathPatch(PlotPath(vv,codes),facecolor=color,edgecolor=edge,lw=.5,alpha=alpha))
def outline(ax,polys,color):
    for p in polys:
        q=np.vstack([p,p[0]]);ax.plot(q[:,0],q[:,1],color=color,ls='--',lw=.8)
fig,axes=plt.subplots(1,3,figsize=(15,6.2),dpi=145)
ax=axes[0]
for name,col in [('Yaw_Base','#b8c8d4'),('Pitch_Yoke','#a8c8bd'),('Yaw_Reaction_Link','#c8b59f'),('Yaw_Bearing','#c7c4d0')]:
    fill(ax,sec['radial45'][name],col)
fill(ax,sec['radial45']['Yaw_Base_removed'],'#ce7372',edge='none')
outline(ax,sec['radial45']['Yaw_Base_before'],'#65747f')
ax.plot(path[:,0],path[:,1],color='#087f87',lw=2)
for target_angle in (-math.pi/3,-math.pi/6):
    ids=np.flatnonzero((path[:,1]<149)&(path[:,2]<0));i=ids[np.argmin(abs(path[ids,2]-target_angle))]
    r,z,a=path[i];axis=np.array([math.sin(a),math.cos(a)]);normal=np.array([math.cos(a),-math.sin(a)])
    box=[(np.array([r,z])+w*normal+l*axis).tolist() for w,l in [(-.5,0),(.5,0),(.5,4.1),(-.5,4.1)]]
    fill(ax,[box],'#edb257',edge='#956526')
ax.set(xlim=(3.5,23),ylim=(134.5,154),aspect='equal',xlabel='径向距离 / mm',ylabel='Z / mm',title='临时进线：R10，竖直起点 Z148')
ax.grid(alpha=.12)
for ax,z,name,title,lim in [(axes[1],145.,'Yaw_Base','承重桥下通道：只扩已有槽',10.),(axes[2],152.5,'Pitch_Yoke','轴颈内通道：外配合面保持',11.)]:
    s=sec['Z'+str(z)]
    fill(ax,s[name],'#a8c8bd');fill(ax,s[name+'_removed'],'#ce7372',edge='none')
    outline(ax,s[name+'_before'],'#65747f');fill(ax,s['Yaw_Reaction_Link'],'#c8b59f')
    ax.set(xlim=(-lim,lim),ylim=(-lim,lim),aspect='equal',xlabel='X / mm',ylabel='Y / mm',title=title+'\nZ='+str(z)+' mm')
    ax.grid(alpha=.12)
fig.suptitle('较大端子预留的颈部候选｜尚未应用到主模型',fontsize=17)
fig.legend([Patch(facecolor='#edb257'),Patch(facecolor='#ce7372'),plt.Line2D([],[],color='#087f87',lw=2),plt.Line2D([],[],color='#65747f',ls='--')],
           ['端子预留体（估算）','本次新增去除区','临时尾线引导路线','上一份候选轮廓'],loc='lower center',bbox_to_anchor=(.5,.09),ncol=4,fontsize=10)
wall=check['finite_journal_wall_samples'];old=wall['before']['minimum']['thickness_mm'];new=wall['candidate']['minimum']['thickness_mm']
fig.text(.04,.025,f'同一 1 × 1.8 × 4.1 mm 端子预留；保持 0.3 mm 模型间隙。轴颈径向壁厚最小样本 {old:.2f} → {new:.2f} mm。\n只完成颈部局部穿入及导线回位；身体余线、完整装配和实物/强度验证仍未完成。',fontsize=10.5)
fig.tight_layout(rect=(0,.2,1,.93));fig.savefig(OUT/'comparison.png',facecolor='#f6f8f8');plt.close(fig)
report=dict(status='PASS',scope='Plots derived from verified saved candidate sections',script_sha256=sha(SCRIPT),
    verification_sha256=sha(OUT/'verification.json'),sections_sha256=sha(OUT/'verified_sections.json'),
    output_sha256=sha(OUT/'comparison.png'),main_applied=False)
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LARGER_NECK_PLOT PASS')
