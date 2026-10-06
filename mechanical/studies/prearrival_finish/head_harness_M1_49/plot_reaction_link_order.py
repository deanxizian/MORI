"""Draw exact current-candidate sections, without modifying CAD geometry."""
from pathlib import Path
import hashlib,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
REST=HERE/'remaining_routes/cam_restraints';OUT=REST/'inner_head_sequence_review';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=REST/'reaction_link_order/sections.json';report=source.parent/'review.json';r=json.loads(report.read_text())
assert sha(source)==r['sections_sha256'] and r['section_plane']=='X=0; plotted coordinates Y,Z'
s=json.loads(source.read_text());font=FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11})
colors={'Body_Upper':'#b3c6cc','Yaw_Base':'#93a3aa','Pitch_Yoke':'#496674','Yaw_Reaction_Link':'#d1ac69','driver':'#337bd4'}
def draw(ax,items):
    for n,polygons in items.items():
        v=[];c=[]
        for p in polygons:
            if not p:continue
            v.extend(p+[p[0]]);c.extend([MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY])
        if v:ax.add_patch(PathPatch(MP(v,c),facecolor=colors[n],edgecolor='#34444a',lw=.7,alpha=.9))
fig,(a,b)=plt.subplots(1,2,figsize=(12,6.4));fig.patch.set_facecolor('#f5f7f8')
draw(a,s['throat']);a.set(xlim=(-19,19),ylim=(157,212),aspect='equal',xlabel='Y / mm',ylabel='Z / mm')
a.set_title('连杆预先固定：当前竖直路径受阻',fontsize=13)
a.annotate('上端夹口被支架内孔挡住',xy=(11,192),xytext=(-17,207),fontsize=10,color='#8b5126',arrowprops=dict(arrowstyle='->',color='#8b5126'))
a.text(.5,.025,'此图：支架抬高 24 mm 的实体截面\n该位置的相交体积约 411 mm³',transform=a.transAxes,ha='center',va='bottom',fontsize=10,bbox=dict(facecolor='white',edgecolor='#d3dade',boxstyle='round,pad=.5'))
draw(b,s['retainer']);b.set(xlim=(-15,115),ylim=(125,205),aspect='equal',xlabel='Y / mm',ylabel='Z / mm')
b.set_title('连杆随头部落座：还需解决工具入口',fontsize=13)
b.annotate('直柄工具穿过上壳',xy=(64,142.5),xytext=(53,174),fontsize=10,color='#21599c',arrowprops=dict(arrowstyle='->',color='#21599c'))
b.text(.5,.025,'直柄 Ø2.5 × 100 mm 仅为规划包络\n扬声器也受碰撞；本截面未绘出扬声器',transform=b.transAxes,ha='center',va='bottom',fontsize=10,bbox=dict(facecolor='white',edgecolor='#d3dade',boxstyle='round,pad=.5'))
for ax in [a,b]:ax.grid(alpha=.16)
fig.suptitle('压板工具路径通过，反力连杆的装配顺序仍待解决',fontsize=16,y=.96)
fig.legend(handles=[Patch(color=colors[n],label=label) for n,label in [('Pitch_Yoke','头部支架'),('Yaw_Reaction_Link','反力连杆'),('Yaw_Base','承重桥'),('Body_Upper','上壳'),('driver','工具规划包络')]],loc='lower center',bbox_to_anchor=(.5,.055),ncol=5,frameon=False)
fig.text(.5,.025,'X = 0 实体剖面。采用独立 C6/导向候选供诊断；主模型未改变。舵盘连接仍待厂家资料。',ha='center',fontsize=10)
fig.subplots_adjust(left=.07,right=.98,bottom=.23,top=.82,wspace=.23)
image=OUT/'reaction_order.png';fig.savefig(image,dpi=160);plt.close(fig)
result=dict(status='PASS',scope='Exact-section diagnostic illustration',inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,report]},image=image.name,image_sha256=sha(image),script_sha256=sha(Path(__file__)),actual_command=[sys.executable,*sys.argv])
(OUT/'plot_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('REACTION_LINK_PLOT_DONE')
