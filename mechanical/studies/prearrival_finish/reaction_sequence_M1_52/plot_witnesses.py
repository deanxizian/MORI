"""Plot saved solid sections with the actual collision location highlighted."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch,Circle
from matplotlib.font_manager import FontProperties
OUT=Path(__file__).resolve().parent;d=json.loads((OUT/'witness_sections.json').read_text())
font=FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':11})
fig,axs=plt.subplots(1,2,figsize=(11,6));colors={'host':'#a6c0ca','link':'#e0b26c','overlap':'#d7544b'}
for ax,r in zip(axs,d['rows']):
    for name in ['host','link','overlap']:
        vv=[];cc=[]
        for p in r['sections'][name]:
            if len(p)<3:continue
            vv+=p+[p[0]];cc+=[MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY]
        if vv:ax.add_patch(PathPatch(MP(vv,cc),facecolor=colors[name],edgecolor='#374b52',lw=.6))
    y,z=r['focus_yz_mm'];ax.add_patch(Circle((y,z),1.0,fill=False,edgecolor='#d7544b',lw=2))
    ax.set(xlim=(y-12,y+12),ylim=(z-12,z+12),aspect='equal',xlabel='Y / mm',ylabel='Z / mm')
    title=('向上' if r['direction_z']==1 else '向下')+f'直进 {r["travel_mm"]:g} mm 后相交'
    ax.set_title(title,fontsize=13);ax.grid(alpha=.15)
    ax.text(.03,.03,f'局部剖面 X={r["plane_x_mm"]:.3f} mm\n实体相交 {r["overlap_mm3"]:.6f} mm³',transform=ax.transAxes,fontsize=10,
            bbox=dict(facecolor='white',edgecolor='#d0d8dc',boxstyle='round,pad=.4'))
fig.suptitle('M1.52 · 夹口连杆的两种直进方向均受阻',fontsize=17,y=.98)
fig.legend(handles=[Patch(color=colors['host'],label='当前头部转动座'),Patch(color=colors['link'],label='当前夹口连杆'),Patch(color=colors['overlap'],label='相交；圆圈标示位置')],loc='lower center',bbox_to_anchor=(.5,.045),ncol=3,frameon=False)
fig.text(.5,.01,'真实实体剖面；这不证明所有复杂路径都不可能。配套舵盘与最终夹紧尺寸仍待厂家资料。',ha='center',fontsize=10)
fig.subplots_adjust(left=.08,right=.99,bottom=.18,top=.88,wspace=.3)
fig.savefig(OUT/'blocked_paths.png',dpi=145);plt.close(fig)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'plot_receipt.json').write_text(json.dumps(dict(status='PASS',source_blend_sha256=d['source_blend_sha256'],sections_sha256=sha(OUT/'witness_sections.json'),
    image='blocked_paths.png',image_sha256=sha(OUT/'blocked_paths.png'),script_sha256=sha(Path(__file__))),indent=2)+'\n')
