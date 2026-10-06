"""Plot exact solid slices from the assembly-order diagnostic."""
from pathlib import Path
import hashlib,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/cam_restraints/power_sequence_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=OUT/'sections.json';report=OUT/'geometry_review.json';r=json.loads(report.read_text())
assert r['status']=='PASS' and sha(source)==r['section_sha256'];sections=json.loads(source.read_text())
font=FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11})
colors={'Body_Upper':'#82afbe','Yaw_Base':'#91a0a8','Pitch_Yoke':'#455d6b','Head_Front':'#eee7da',
        'Head_Rear':'#eee7da','Load_Frame':'#c4cbd0','Yaw_Base_1_Screw':'#b0987c'}
def draw(ax,items,override=None):
    for n,polygons in items.items():
        v=[];c=[]
        for p in polygons:
            if not p:continue
            v.extend(p+[p[0]]);c.extend([MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY])
        if v:ax.add_patch(PathPatch(MP(v,c),facecolor=override or colors[n],edgecolor='#34444a',lw=.75,alpha=.9))
fig,(a,b)=plt.subplots(1,2,figsize=(12,6.5),gridspec_kw={'width_ratios':[1.1,1]})
fig.patch.set_facecolor('#f5f7f8')
draw(a,sections['lifted']);a.set(xlim=(-75,75),ylim=(95,315),aspect='equal',xlabel='X / mm',ylabel='Z / mm')
a.set_title('头部＋承重桥抬高 19 mm\n上壳倾斜 15°、抬高 14 mm',fontsize=13)
a.text(.5,.025,'383 个位置：未检出实体相交\n尚未验证连续净距、带线及锁紧',transform=a.transAxes,ha='center',va='bottom',fontsize=10,
       bbox=dict(facecolor='white',edgecolor='#d3dade',boxstyle='round,pad=.6'))
draw(b,{n:p for n,p in sections['closed'].items() if n in ['Body_Upper','Yaw_Base','Load_Frame','Yaw_Base_1_Screw']})
draw(b,sections['withdrawn_screw_2mm'],'#ef906b')
b.set(xlim=(43,63),ylim=(97,115),aspect='equal',xlabel='X / mm',ylabel='Z / mm')
b.set_title('上壳合拢后的右侧螺钉\n实际螺钉向外移动 2 mm 时相交',fontsize=13)
b.annotate('与上壳相交',xy=(52.3,105.5),xytext=(53.7,112),fontsize=11,color='#9b3d21',
           arrowprops=dict(arrowstyle='->',color='#9b3d21'))
b.text(.5,.015,'相交体积约 5.50 mm³；左侧对称\n这是实际螺钉实体检查，非扫掠凸包误报',transform=b.transAxes,ha='center',va='bottom',fontsize=10,
       bbox=dict(facecolor='white',edgecolor='#d3dade',boxstyle='round,pad=.6'))
for ax in [a,b]:ax.grid(alpha=.15)
fig.suptitle('头身整体装入：刚体路径有进展，闭壳锁紧仍受阻',fontsize=16,y=.96)
fig.legend(handles=[Patch(color=colors['Body_Upper'],label='身体上壳'),Patch(color=colors['Yaw_Base'],label='承重桥'),
                    Patch(color=colors['Pitch_Yoke'],label='头部支架'),Patch(color='#ef906b',label='外移 2 mm 的螺钉')],
           loc='lower center',bbox_to_anchor=(.5,.055),ncol=4,frameon=False)
fig.text(.5,.025,'当前 M1.49 实体截面：左图 Y = −1，右图 Y = 0 mm。主模型未修改；该装配顺序尚未采用。',ha='center',fontsize=10)
fig.subplots_adjust(left=.07,right=.97,bottom=.21,top=.81,wspace=.2)
image=OUT/'assembly_access.png';fig.savefig(image,dpi=160);plt.close(fig)
result=dict(status='PASS',scope='Actual-section review illustration',inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,report]},
            image=image.name,image_sha256=sha(image),script_sha256=sha(Path(__file__)),actual_command=[sys.executable,*sys.argv])
(OUT/'plot_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('HEAD_MODULE_ACCESS_PLOT_DONE')
