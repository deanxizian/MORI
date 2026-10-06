"""Source-derived radial sections and journal comparison, not concept art."""
from pathlib import Path
import json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Patch,Circle
from matplotlib import font_manager
HERE=Path(__file__).resolve().parent;OUT=HERE/'assembly_feed_v3'
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Light.ttc')
plt.rcParams.update({'font.family':'Heiti SC','axes.unicode_minus':False,'svg.fonttype':'none'})
sections=json.loads((OUT/'sections.json').read_text())['45']
feed=json.loads((OUT/'coupled_feed_screen.json').read_text());chosen=next(r for r in feed['tested_cases'] if r['radius_mm']==feed['selected_radius_mm'])
travel=np.array(chosen['radial_z_axis_angle'])
route=json.loads((HERE/'joined_entry_screen.json').read_text());installed=next(r for r in route['rows'] if r['yaw_deg']==0 and r['azimuth_deg']==45)
wall=json.loads((OUT/'journal_sections.json').read_text())

def fill(ax,polys,color,alpha=1.,edge='#55616b',lw=.5):
    vv=[];codes=[]
    for p in polys:
        p=np.array(p).tolist()
        if len(p)<3:continue
        vv.extend(p+[p[0]]);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(p)-1)+[PlotPath.CLOSEPOLY])
    if vv:ax.add_patch(PathPatch(PlotPath(vv,codes),facecolor=color,edgecolor=edge,lw=lw,alpha=alpha))
def outlines(ax,polys,color,ls='--',lw=.8):
    for p in polys:
        a=np.vstack([p,p[0]]);ax.plot(a[:,0],a[:,1],color=color,ls=ls,lw=lw)

fig,axes=plt.subplots(1,2,figsize=(12,8),dpi=155)
colors={'Yaw_Base_J3':'#b8c8d4','Pitch_Yoke_J3':'#b4cdc3','Yaw_Reaction_Link':'#c8b59f','Yaw_Bearing':'#c7c4d0','Yaw_Servo':'#e0d4c3','Pitch_Servo':'#e0d4c3'}
for ax,(name,xlim,ylim,title,curve_key,indices) in zip(axes,[
    ('Yaw_Base',(3,22),(135,155),'身体侧：刚性端子前伸，尾部连着软线','lower_curve_body_mm',[55,103]),
    ('Pitch_Yoke',(3,24),(173,208),'头侧：R8 出口，穿出后再移至装后线形','upper_curve_yaw_mm',[412,473])]):
    for part,color in colors.items():fill(ax,sections[part],color)
    fill(ax,sections[name+'_newly_removed'],'#d56c68',.8,edge='none')
    outlines(ax,sections[name+'_J2'],'#667483',lw=.7)
    w=np.array(installed[curve_key]);ax.plot(np.linalg.norm(w[:,:2],axis=1),w[:,2],color='#76558c',lw=2.0)
    ax.plot(travel[:,0],travel[:,1],color='#087f87',lw=2.1)
    for index in indices:
        r,z,a=travel[index];axis=np.array([math.sin(a),math.cos(a)]);cross=np.array([math.cos(a),-math.sin(a)])
        corners=np.array([np.array([r,z])+s*.4*cross+d*axis for s,d in [(-1,0),(1,0),(1,3.9),(-1,3.9)]])
        fill(ax,[corners.tolist()],'#edb257',.9,edge='#956526',lw=.8)
        ax.scatter(r,z,s=14,color='#087f87',zorder=7)
    ax.set(xlim=xlim,ylim=ylim,aspect='equal',title=title,xlabel='径向距离 / mm',ylabel='Z / mm');ax.grid(alpha=.12)
fig.suptitle('J3 独立候选：端子与尾线一起穿过关节',fontsize=17)
fig.legend([Patch(facecolor='#edb257'),plt.Line2D([],[],color='#087f87',lw=2),plt.Line2D([],[],color='#76558c',lw=2),Patch(facecolor='#d56c68'),plt.Line2D([],[],color='#667483',ls='--')],
           ['裸端子名义包络','临时软线路径','装后导线径向投影','相对 J2 新增去除区','J2 轮廓'],loc='lower center',bbox_to_anchor=(.5,.085),ncol=3,fontsize=10)
fig.text(.07,.028,'点标在端子尾部；前端沿切线伸出 3.9 mm。中央角向松量未在径向投影中展开。\n仅四根 UART 线的局部装配候选；主模型未改，真实压接外形、完整尾线操作和固定仍待完成。',fontsize=10.5)
fig.tight_layout(rect=[0,.19,1,.93]);fig.savefig(OUT/'coupled_feed_sections.png',facecolor='#f6f8f8');plt.close(fig)

main=wall['wall_samples']['main'];new=wall['wall_samples']['J3'];minwall=new['minimum'];angle=math.radians(minwall['angle_deg']);er=np.array([math.cos(angle),math.sin(angle)])
old_area=min(r['area_mm2'] for r in main['section_properties_within_nominal_journal_cylinder'])
new_area=min(r['area_mm2'] for r in new['section_properties_within_nominal_journal_cylinder'])
fig,(ax,tx)=plt.subplots(1,2,figsize=(12,6.5),dpi=155,gridspec_kw={'width_ratios':[1.2,1]})
fill(ax,wall['xy_section_polygons']['main'],'#e1e6e9',edge='#96a3ae')
fill(ax,wall['xy_section_polygons']['J3'],'#9fbdb3',edge='#446256')
outlines(ax,wall['xy_section_polygons']['J2'],'#586b7b',lw=.85)
for phase in [45,135,225,315]:
    a=math.radians(phase);point=7.6*np.array([math.cos(a),math.sin(a)])
    ax.add_patch(Circle(point,.3302,facecolor='#de9b3d',edgecolor='none',zorder=5))
ax.plot(*np.array([er*minwall['inner_r_mm'],er*minwall['outer_r_mm']]).T,color='#b74a49',lw=3)
ax.annotate(f"抽样最薄 {minwall['thickness_mm']:.2f} mm",xy=er*(minwall['inner_r_mm']+.7),xytext=(-10.5,12.3),
            arrowprops={'arrowstyle':'->','color':'#b74a49'},fontsize=11,color='#9c403f')
ax.set(xlim=(-12,12),ylim=(-12,14),aspect='equal',xlabel='X / mm',ylabel='Y / mm',title=f"轴颈截面 Z={wall['xy_section_z_mm']:.2f} mm");ax.grid(alpha=.12)
tx.axis('off');tx.text(.02,.96,'轴颈内部增加穿线空间',fontsize=18,va='top')
text=[f"名义轴颈外径：{2*wall['journal_outer_nominal_radius_mm']:.2f} mm（不变）",
      f"原径向壁厚最小样本：{main['minimum']['thickness_mm']:.2f} mm",
      f"J3 径向壁厚最小样本：{minwall['thickness_mm']:.2f} mm",
      f"截面积最小样本：{old_area:.2f} → {new_area:.2f} mm²",
      f"上述截面积减少：{100*(1-new_area/old_area):.2f}%",
      '',f"圆柱段 16 个截面，{new['valid_rays']} 条有效射线。",
      '入口倒角另 720 条不计入圆柱壁厚。',
      '只测名义轴颈圆柱内的径向材料，', '不代表全部打印件的最小壁厚。','',
      '未应用主模型；PA12 强度、压配、冲击', '和带线实际操作仍需验证。']
tx.text(.02,.84,'\n'.join(text),va='top',fontsize=11.5,linespacing=1.8)
fig.suptitle('结构代价明确保留：局部壁厚变薄，轴颈外配合面不变',fontsize=17)
fig.tight_layout(rect=[0,.03,1,.91]);fig.savefig(OUT/'journal_comparison.png',facecolor='#f6f8f8');plt.close(fig)
print('COUPLED_FEED_PLOTS_SAVED',old_area,new_area)
