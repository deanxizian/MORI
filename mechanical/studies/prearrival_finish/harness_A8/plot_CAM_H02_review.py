"""Plot verified saved curves and documented old/new nominal route lengths."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/CAM_H02_joint_lift'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'projections.json').read_text())
assert d['status']=='PASS'
for section in ['source_files','protected_sources']:
    for p,h in d[section].items():assert sha(ROOT/p)==h,p
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'font.size':11})
colours=['#cf5539','#267eb0','#09795d','#8555ad']
fig,axes=plt.subplots(2,3,figsize=(15.3,10.4),dpi=145)
fig.patch.set_facecolor('#f4f7f7')
for col,index in enumerate([0,18,36]):
    v=d['views'][str(index)]
    for row,(plane,axis) in enumerate([('XZ',0),('YZ',1)]):
        ax=axes[row,col]
        for name,polys in v['projections'][plane].items():
            for poly in polys:
                p=np.asarray(poly);p=np.vstack([p,p[0]])
                ax.plot(p[:,0],p[:,1],color='#aebac0',lw=.7,alpha=.65,
                        linestyle='--' if name=='Body_Upper' else '-')
                if name!='Body_Upper':ax.fill(p[:,0],p[:,1],color='#dce4e8',alpha=.2)
        for name,polys in d['body_projections'][plane].items():
            for poly in polys:
                p=np.asarray(poly)
                ax.fill(p[:,0],p[:,1],color='#253e40' if 'H02' in name else '#89969a',alpha=.7)
        for pin,p in v['curves'].items():
            p=np.asarray(p);c=colours[int(pin)-1]
            ax.plot(p[:,axis],p[:,2],color=c,lw=1.65)
            ax.scatter(p[0,axis],p[0,2],color=c,s=15,marker='s',zorder=6)
        ax.set_xlim(-66,66);ax.set_ylim(126,223);ax.set_aspect('equal')
        ax.set_title(f"桥上移 {v['bridge_z_mm']:g} mm · {plane}",fontsize=13)
        ax.set_xlabel(plane[0]+' / mm');ax.set_ylabel('Z / mm');ax.grid(alpha=.14)
fig.suptitle('CAM 与 H02 联合走向：37 个有限抬升位置通过',fontsize=19,y=.985,color='#223b41')
handles=[Line2D([0],[0],color=c,lw=2,label=f'CAM {i+1}') for i,c in enumerate(colours)]
handles += [Line2D([0],[0],color='#253e40',lw=3,label='新 H02 走向'),Line2D([0],[0],color='#89969a',lw=3,label='其余身体线')]
fig.legend(handles=handles,ncol=6,loc='upper center',bbox_to_anchor=(.5,.94),frameon=False)
fig.text(.055,.088,'图示是同一组导线在已检查阶段的三个位置；连续区间、完整装配和实物操作尚未通过。',fontsize=11.5,color='#765222')
fig.text(.055,.032,'身体端口、针序和全长分配保持；这里只展示身体附近，上方余线未画全。\n独立研究使用尚未采用的打印候选，主模型 M1.47 未改。二维投影重叠不等于三维相交。',fontsize=10.5,color='#56696b',linespacing=1.6)
fig.subplots_adjust(top=.866,bottom=.155,left=.055,right=.982,hspace=.29,wspace=.22)
fig.savefig(OUT/'lift_comparison.png');plt.close(fig)

old=next(r for r in d['old_h02'] if r['id']=='H02_2')
new=next(r for r in d['new_h02'] if r['id']=='H02_2')
oldp=np.asarray(old['curve_mm']);newp=np.asarray(new['curve_mm'])
fig,axes=plt.subplots(1,2,figsize=(12.8,5.5),dpi=150)
for ax,(a,b,title) in zip(axes,[(0,1,'俯视走向 · XY'),(1,2,'高度变化 · YZ')]):
    ax.plot(oldp[:,a],oldp[:,b],color='#899399',lw=2,ls='--',label='此前候选')
    ax.plot(newp[:,a],newp[:,b],color='#168477',lw=2,label='联合检查候选')
    for p in [newp[0],newp[-1]]:ax.scatter(p[a],p[b],marker='s',s=40,color='#273c45',zorder=5)
    ax.set_aspect('equal');ax.grid(alpha=.18);ax.set_title(title)
    ax.set_xlabel('XYZ'[a]+' / mm');ax.set_ylabel('XYZ'[b]+' / mm');ax.legend(loc='best',frameon=False)
fig.suptitle('只调整 H02 第二根线的中段，两个端点保持',fontsize=17,y=.982)
delta=new['analytic_length_mm']-old['analytic_length_mm']
fig.text(.055,.045,f"名义路线长 {old['analytic_length_mm']:.3f} → {new['analytic_length_mm']:.3f} mm（+{delta:.3f} mm）；模型线形峰值 {oldp[:,2].max():.3f} → {newp[:,2].max():.3f} mm。\n这是几何路线长度，不是供应商裁线尺寸；弯曲半径与端后直段保持。",fontsize=10.5,linespacing=1.7,color='#4c6165')
fig.subplots_adjust(top=.85,bottom=.22,left=.07,right=.975,wspace=.26)
fig.savefig(OUT/'H02_comparison.png');plt.close(fig)
w=d['rear_J2_witness'];center=np.asarray(w['center_mm'])
fig,axes=plt.subplots(1,2,figsize=(11.2,5.3),dpi=160)
for ax,(plane,axis) in zip(axes,[('XZ',0),('YZ',1)]):
    for name,colour in [('Load_Frame','#d2dde1'),('Plug_rear_J2','#d79553'),('overlap','#c73232')]:
        for poly in w['projections'][plane][name]:
            p=np.asarray(poly);ax.fill(p[:,0],p[:,1],color=colour,alpha=.78)
    ax.scatter(center[axis],center[2],s=140,facecolors='none',edgecolors='#b52930',linewidths=1.5,zorder=7)
    ax.set_xlim(center[axis]-8,center[axis]+8);ax.set_ylim(center[2]-7,center[2]+7)
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(plane+' 局部投影')
    ax.set_xlabel(plane[0]+' / mm');ax.set_ylabel('Z / mm')
fig.suptitle('后板 J2 插头包络与托板：原外壳保持位置需调整',fontsize=16.5,y=.98)
fig.text(.055,.06,f"外壳倾斜 15°、抬高 14 mm；灰色为托板，橙色为插头分配，红色为名义重叠 {w['intersection_mm3']:.5f} mm³。\n插头外形含保守包络，这不是实物相撞的证明；不能据此直接删减打印件或插头。",fontsize=10.5,linespacing=1.6,color='#5b4a3d')
fig.subplots_adjust(top=.84,bottom=.22,left=.08,right=.97,wspace=.25)
fig.savefig(OUT/'rear_J2_overlap.png');plt.close(fig)
report=dict(status='PASS',script_sha256=sha(SCRIPT),
            source_files={str((OUT/'projections.json').relative_to(ROOT)):sha(OUT/'projections.json')},
            outputs={n:sha(OUT/n) for n in ['lift_comparison.png','H02_comparison.png','rear_J2_overlap.png']},
            old_H02_2_length_mm=old['analytic_length_mm'],new_H02_2_length_mm=new['analytic_length_mm'],
            old_H02_2_polyline_peak_z_mm=float(oldp[:,2].max()),new_H02_2_polyline_peak_z_mm=float(newp[:,2].max()),
            main_applied=False,supplier_cut_lengths=False)
(OUT/'plot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_H02_PLOTS_SAVED')
