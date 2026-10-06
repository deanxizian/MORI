"""Illustrate the verified upper-entry path in the source coordinate system."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/PH_shell16_stepped_entry'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((OUT/'projections.json').read_text());v=json.loads((OUT/'verification.json').read_text())
assert data['verification_sha256']==sha(OUT/'verification.json') and v['status']=='PASS'
assert v['source_screen_sha256']==sha(OUT/'screen.json')
lead=json.loads((OUT/'exit_leads.json').read_text());assert lead['status']=='PASS'
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':10})
colors={'Body_Upper':'#a4b7bd','Yaw_Base':'#518791','Load_Frame':'#8a999d','MCU_Carrier':'#658e74','MCU_Motion':'#759e77','E_Straight_Header':'#d0a25c'}
world=np.asarray(data['withdrawal_translation_mm'])+np.asarray(data['housing_center_mm'])
world=world[::-1]
fig,axs=plt.subplots(1,2,figsize=(13,7.6),dpi=160)
for ax,(plane,dims) in zip(axs,[('YZ',[1,2]),('XZ',[0,2])]):
    for name,polys in data['projections'][plane].items():
        color=colors.get(name,'#ada0bd')
        for poly in polys:
            pp=np.asarray(poly);pp=np.vstack([pp,pp[0]])
            ax.plot(pp[:,0],pp[:,1],color=color,lw=.8,alpha=.85)
    path=world[:,dims]
    ax.plot(path[:,0],path[:,1],'-o',color='#b5472f',lw=2.2,ms=4,label='PH胶壳中心：装入方向')
    ax.plot(path[0,0],path[0,1],'s',color='#b5472f',ms=7)
    ax.plot(path[-1,0],path[-1,1],'*',color='#b5472f',ms=11)
    for a,b in zip(path[:-1],path[1:]):
        delta=b-a
        if np.linalg.norm(delta)>3:
            ax.annotate('',xy=a+.67*delta,xytext=a+.4*delta,arrowprops=dict(arrowstyle='->',color='#b5472f',lw=1.5))
    size=np.asarray(data['housing_dimensions_mm'])[dims]
    for i in [0,3,-1]:
        q=path[i];ax.add_patch(Rectangle(q-size/2,*size,edgecolor='#b5472f',facecolor='none',lw=1.2,alpha=.75))
    ax.set(aspect='equal',xlim=(-82,76) if plane=='YZ' else (-64,64),ylim=(96,214),
           xlabel=('Y' if plane=='YZ' else 'X')+' / mm',ylabel='Z / mm',title=('侧视' if plane=='YZ' else '正视')+' · '+plane+' 投影')
    ax.grid(alpha=.13);ax.legend(loc='upper right',fontsize=9)
fig.suptitle('从上方开口接入 PH：裸胶壳的 7 段平移动作已复核',fontsize=17,color='#28464c',y=.96)
fig.text(.065,.16,'上壳保持 16°、抬高 14 mm；承重桥就位。矩形为未加余量的名义胶壳，三维扫掠另加 0.3 mm 预留。',fontsize=11,color='#45616a')
fig.text(.065,.115,'H02 / H03 保留；H01 / H04 的 10 根线及 4 个插头延后，其后装入尚未完成。',fontsize=11,color='#45616a')
fig.text(.065,.07,'仅胶壳和前 5 mm 直段预留通过；后续柔性导线、手部工具与真实插合未验证。最后 8 mm 插接段保留原生配合例外。',fontsize=10,color='#946321')
fig.text(.065,.03,'二维投影相交不代表三维实体相交。主模型 M1.47 未改，候选未采用，制造图未放行。',fontsize=10,color='#946321')
fig.subplots_adjust(left=.06,right=.98,bottom=.25,top=.88,wspace=.24)
fig.savefig(OUT/'path.png');plt.close(fig)
r=dict(status='PASS',scope='Source-based drawing of bare connector path only',script_sha256=sha(SCRIPT),
       source_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'screen.json',OUT/'verification.json',OUT/'projections.json',OUT/'exit_leads.json']},
       outputs={'path.png':sha(OUT/'path.png')},main_applied=False,manufacturing_release=False)
(OUT/'plot.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('PH_STEPPED_PATH_PLOT')
