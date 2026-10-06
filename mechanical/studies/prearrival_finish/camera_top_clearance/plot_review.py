"""Before/after images plus actual camera-coordinate mesh sections."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import PathPatch,Patch
from matplotlib.path import Path as MP
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((OUT/'construction.json').read_text());r=json.loads((OUT/'render.json').read_text());s=json.loads((OUT/'sections.json').read_text())
assert all(sha(OUT/n)==h for n,h in r['outputs'].items())
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':12})
ink='#233d45';bg='#f7f8f7';green='#26786f';orange='#c76032'
fig,axs=plt.subplots(1,2,figsize=(12,5.9),dpi=160)
for ax,n,t in zip(axs,['before','after'],['原上沿：橙色为拟去除的 0.6 mm','候选：上沿保持整条平直']):
    ax.imshow(plt.imread(OUT/(n+'.png')));ax.axis('off');ax.set_title(t,color=ink,pad=12)
fig.suptitle('相机安装口上沿局部间隙候选',fontsize=19,color=ink,y=.98)
fig.text(.045,.035,'相机、内侧定位面、前壳和孔位保持。无新孔、局部台阶或零件。\n上壁名义厚度 1.8 → 1.2 mm；照片估算的相机尺寸及 PA12 强度仍需实物复核。',color=ink,fontsize=11,linespacing=1.5)
fig.tight_layout(rect=(0,.10,1,.94));fig.savefig(OUT/'comparison.png',facecolor=bg);plt.close(fig)
def fill(ax,polys,color,alpha=1):
    verts=[];codes=[]
    for p in polys:
        if len(p)<3:continue
        verts+=p+[p[0]];codes+=[MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY]
    if verts:ax.add_patch(PathPatch(MP(verts,codes),facecolor=color,edgecolor=color,lw=.8,alpha=alpha))
fig,axs=plt.subplots(1,2,figsize=(12,6.2),dpi=160)
for ax,key,title in [(axs[0],'0.0','中央截面：内侧定位面保持'),(axs[1],'6.0','上角截面：前壳间隙增大')]:
    d=s['sections'][key]
    fill(ax,d['shell'],'#aab4b8');fill(ax,d['original'],'#eeb798');fill(ax,d['candidate'],'#79a5a7');fill(ax,d['camera'],'#b87c3e')
    ax.axhline(6.1,color=orange,ls=':',lw=1);ax.axhline(5.5,color=green,ls=':',lw=1)
    ax.set(xlim=(-6.7,.7),ylim=(2.7,7.2),aspect='equal',xlabel='相机局部 W / mm（向镜头）',ylabel='相机局部 −V / mm（向上）',title=title)
    ax.grid(alpha=.16)
axs[0].annotate('',xy=(-2.6,5.5),xytext=(-2.6,4.3),arrowprops=dict(arrowstyle='<->',color=ink,lw=1.3))
axs[0].text(-2.4,4.75,'1.2 mm',fontsize=12,color=ink)
axs[1].text(-6.3,6.4,'原上沿 6.1',color=orange,fontsize=10)
axs[1].text(-6.3,5.7,'新上沿 5.5',color=green,fontsize=10)
fig.suptitle('真实网格剖面 · 外壳未削薄',fontsize=18,color=ink)
fig.legend([Patch(fc=c) for c in ['#aab4b8','#79a5a7','#eeb798','#b87c3e']],['前壳','候选支架','原上沿（去除部分）','相机参考'],loc='lower center',ncol=4,bbox_to_anchor=(.5,.08))
fig.text(.055,.025,'保存模型：相交 0 mm³，最近间隙约 0.357 mm。整件前壳沿 +Y 合拢 68 mm 的支架间隙连续检查通过。',fontsize=10.5,color=ink)
fig.tight_layout(rect=(0,.17,1,.92));fig.savefig(OUT/'sections.png',facecolor=bg);plt.close(fig)
(OUT/'plots.json').write_text(json.dumps(dict(status='PASS',script_sha256=sha(SCRIPT),render_sha256=sha(OUT/'render.json'),sections_sha256=sha(OUT/'sections.json'),outputs={n:sha(OUT/n) for n in ['comparison.png','sections.png']}),indent=2)+'\n')
print('CAMERA_TOP_PLOTS PASS')
