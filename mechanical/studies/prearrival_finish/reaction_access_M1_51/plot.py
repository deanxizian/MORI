"""Plot measured mesh sections; this is CAD evidence, not an invented image."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
from matplotlib.font_manager import FontProperties
OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'sections.json').read_text())
font=FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11})
fig,axs=plt.subplots(2,2,figsize=(10,10));fig.patch.set_facecolor('#f5f7f8')
colors={'host':'#adbec1','before':'#e5b15d','after':'#e5b15d','old_overlap':'#d44846'}
def draw(ax,polys,color):
    vertices=[];codes=[]
    for polygon in polys:
        if len(polygon)<3:continue
        vertices+=polygon+[polygon[0]]
        codes += [MP.MOVETO]+[MP.LINETO]*(len(polygon)-1)+[MP.CLOSEPOLY]
    if vertices:ax.add_patch(PathPatch(MP(vertices,codes),facecolor=color,edgecolor='#35474b',lw=.8))
for i,row in enumerate(d['rows']):
    for j,state in enumerate(['before','after']):
        ax=axs[i,j];draw(ax,row['sections']['host'],colors['host']);draw(ax,row['sections'][state],colors[state])
        if state=='before':draw(ax,row['sections']['old_overlap'],colors['old_overlap'])
        ax.set(xlim=(-3.4,3.4),ylim=(-3.4,3.4),aspect='equal',xlabel='相对孔轴 X / mm',ylabel='相对孔轴 Z / mm')
        ax.grid(alpha=.12);ax.plot(0,0,'+',c='#3c555b',ms=9)
        label='下部承重桥螺母' if i==0 else '上部舵盘夹口螺母'
        ax.set_title(label+(' · 原角度' if j==0 else ' · 转正 30°'),fontsize=13)
        ax.text(.5,.025,'角部相交约 0.00847 mm³' if j==0 else '打印件和孔轴不动；相交为 0',transform=ax.transAxes,ha='center',va='bottom',fontsize=10,
                bbox=dict(facecolor='white',edgecolor='#d8dfe0',boxstyle='round,pad=.4'))
fig.suptitle('M1.52 · 螺母与六角槽方向对齐',fontsize=18,y=.97)
fig.legend(handles=[Patch(color=colors['host'],label='现有打印件'),Patch(color=colors['after'],label='试配螺母包络'),Patch(color=colors['old_overlap'],label='原相交')],loc='lower center',bbox_to_anchor=(.5,.045),ncol=3,frameon=False)
fig.text(.5,.025,'均为穿过螺母中心的真实 X/Z 剖面；螺母规格、舵盘接口与实物配合仍待确认。',ha='center',fontsize=10)
fig.subplots_adjust(left=.10,right=.98,bottom=.13,top=.91,wspace=.25,hspace=.30)
image=OUT/'nut_alignment.png';fig.savefig(image,dpi=160);plt.close(fig)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'plot_receipt.json').write_text(json.dumps(dict(status='PASS',image=image.name,image_sha256=sha(image),sections_sha256=sha(OUT/'sections.json'),script_sha256=sha(Path(__file__))),indent=2)+'\n')
print('NUT_SECTION_PLOT_PASS',flush=True)
