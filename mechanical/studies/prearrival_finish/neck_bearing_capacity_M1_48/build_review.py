"""Publish actual candidate sections and scoped results, never main geometry."""
from pathlib import Path
from html.parser import HTMLParser
import json,hashlib,datetime,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((HERE/n).read_text())
b=read('C2_build.json');v=read('C2_verification.json');p=read('packing.json');s=read('posed_sections.json')
assert b['source_main_sha256']==v['source_main_sha256']==p['source_main_sha256']==s['source_main_sha256']
assert b['script_sha256']==sha(HERE/'build_candidate_v2.py')
assert v['build_sha256']==sha(HERE/'C2_build.json') and v['script_sha256']==sha(HERE/'verify_candidate.py')
assert s['verification_sha256']==sha(HERE/'C2_verification.json')

class Text(HTMLParser):
    def __init__(self):super().__init__();self.out=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ['script','style']:self.skip+=1
    def handle_endtag(self,t):
        if t in ['script','style']:self.skip-=1
    def handle_data(self,d):
        if not self.skip and d.strip():self.out.append(d.strip())
sources=[]
for name,d,D,mass,da,Da,url in [
    ('6804ZZ',20,32,.017,22,30,'https://www.oss.nsk.com/tw/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6804zz-dgbb-sr.html'),
    ('6806ZZ',30,42,.024,32,40,'https://www.oss.nsk.com/tw/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6806zz-apn.html')]:
    path=HERE/'sources'/('NSK_'+name+'.html');parser=Text();parser.feed(path.read_text());text='\n'.join(parser.out)
    for token in [f'd\n{d}\nmm',f'D\n{D}\nmm','B\n7\nmm',f'da (min.)\n{da}\nmm',f'Da (max.)\n{Da}\nmm',f'Mass approx.\n{mass}\nkg']:
        assert token in text,(name,token)
    sources.append(dict(manufacturer='NSK',model=name,url=url,archive=str(path.relative_to(ROOT)),sha256=sha(path),
        units='mm except kg mass',documented_fields=dict(d=d,D=D,B=7,r_min=.3,da_min=da,da_max=da,Da_max=Da,ra_max=.3,approx_mass_kg=mass),
        evidence='VENDOR_DOCUMENTED boundary/abutments/catalogue approximate mass',
        full_CAD=False,measured=False,price=None,stock=None,procurement_selected=name=='6804ZZ'))
(HERE/'sources/manifest.json').write_text(json.dumps(dict(sources=sources,no_hardware_scaling=True,
    bearing_mass_delta_g=7.,candidate_not_selected=True),ensure_ascii=False,indent=2)+'\n')

def fill(ax,polys,color,z):
    verts=[];codes=[]
    for a in polys:
        if not a:continue
        verts.extend(a+[a[0]]);codes.extend([MP.MOVETO]+[MP.LINETO]*(len(a)-1)+[MP.CLOSEPOLY])
    if verts:ax.add_patch(PathPatch(MP(verts,codes),facecolor=color,edgecolor='none',zorder=z))
colors=dict(Yaw_Base='#b6c6c0',Pitch_Yoke='#3a819d',Yaw_Anti_Lift_Keeper='#cc9e51',
    Yaw_Bearing='#667581',Yaw_Reaction_Link='#233f35',Head_Rear='#a99aa8',Head_Front='#a99aa8',collision='#e63737')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(12,8.8))
for row,pitch in enumerate([25,-20]):
    for col,tag in enumerate(['current','candidate']):
        ax=axes[row,col];layers=s['sections'][f'{tag}_{pitch}']
        for i,n in enumerate(['Yaw_Base','Yaw_Bearing','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link','Head_Rear','Head_Front','collision']):
            if n in layers:fill(ax,layers[n],colors[n],i+1)
        ax.set_aspect('equal');ax.set_xlim((-24,-3) if pitch==25 else (12,28));ax.set_ylim((157,173) if pitch==25 else (157,171))
        ax.grid(alpha=.12);ax.set_facecolor('#fafbf9');ax.set_xlabel('Y (mm)');ax.set_ylabel('Z (mm)')
        ax.set_title(('Current main M1.48' if col==0 else 'Unadopted 6806 candidate C2')+f'\nPitch {pitch:+d} deg, X = 0 section')
fig.suptitle('Larger neck corridor: full head motion still conflicts',fontsize=18,y=.98)
fig.legend(handles=[Patch(color=colors[n],label=label) for n,label in [('Yaw_Base','Fixed print'),('Pitch_Yoke','Yaw support'),
    ('Yaw_Anti_Lift_Keeper','Keeper'),('Head_Rear','Pitched head shell'),('collision','Solid intersection')]],
    loc='lower center',ncol=5,frameon=False,bbox_to_anchor=(.5,.015))
fig.subplots_adjust(top=.89,bottom=.12,hspace=.43,wspace=.25)
fig.savefig(HERE/'head_motion_sections.png',dpi=170,facecolor='white');fig.savefig(HERE/'head_motion_sections.svg',facecolor='white');plt.close(fig)

sec=read('C2_sections.json');fig,axes=plt.subplots(1,2,figsize=(11,5.4))
for j,(z,lim,title) in enumerate([(146.,15,'Reaction socket and two wire windows'),(152.5,25,'Larger bearing and11local conductors')]):
    ax=axes[j];layers=sec['Z'+str(z)]
    for i,n in enumerate(['Yaw_Base','Yaw_Bearing','Pitch_Yoke','Yaw_Reaction_Link']):fill(ax,layers[n],colors[n],i+1)
    data=np.load(HERE/'packed_curves.npz')
    for i,slot in enumerate(p['selected']):
        points=data[f'wire{i}_y0'];x=np.interp(z,points[:,2],points[:,0]);y=np.interp(z,points[:,2],points[:,1])
        ax.add_patch(plt.Circle((x,y),slot['OD_mm']/2,color='#cf763b',zorder=9))
    ax.set_aspect('equal');ax.set_xlim(-lim,lim);ax.set_ylim(-lim,lim);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.12)
    ax.set_title(title+f'\nZ = {z:g} mm, yaw 0 deg');ax.set_facecolor('#fafbf9')
fig.suptitle('Local clearance passes; this is not the whole harness',fontsize=17,y=.97)
fig.subplots_adjust(top=.78,bottom=.12,wspace=.24);fig.savefig(HERE/'local_sections.png',dpi=170,facecolor='white');plt.close(fig)

gap=p['minimum_pair_gap_lower_bound_mm'];summary=dict(status='BLOCKED',source_main_sha256=b['source_main_sha256'],
    scope='Larger bearing plus complete print candidate, not adopted',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),local_wire_clearance=b['status'],
    local_pair_gap_lower_bound_mm=gap,socket_material_loss_mm3=b['protected_material_removed_mm3']['socket'],
    changed_prints=['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper'],bearing_boundary_change_mm=[[20,32,7],[30,42,7]],
    bearing_mass_delta_g=7,complete_parts_motion=v['status'],new_collision_records=len(v['new_overlaps']),
    conflict_pairs=sorted({tuple(sorted([r['a'],r['b']])) for r in v['new_overlaps']}),
    stop_onset_sample_deg=[r['hit']['first_sampled_overlap_deg'] for r in v['stop_contacts']],
    rigid_local_installation='PASS' if not any([v['keeper_bench_side']['hits'],v['paired_vertical_insertion']['hits'],v['bearing_insertion']['hits'],v['tool_access']['hits'],v['screw_insertion_hits']]) else 'BLOCKED',
    full_endpoints='NOT_TESTED',wired_assembly='NOT_TESTED',actual_wire_selection='BLOCKED',whole_harness='BLOCKED',
    main_applied=False,manufacturing_release=False,
    next_work='Resolve rotating neck/head shell space together, preserve the source shell/optical axes, then recheck whole motion before routing endpoints.',
    evidence={n:sha(HERE/n) for n in ['packing.json','C1_build.json','C2_build.json','C2_verification.json','posed_sections.json','sources/manifest.json']})
(HERE/'review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
readme=f'''# 6806跨颈通道评估，主模型仍为M1.48

**BLOCKED；独立候选未采用。到货前仍有5类待办，完整线束是主要未完成项。**

原20×32×7轴承内侧的通道会损伤反力座。另一条外绕路线把活动段移到压板上方后，1296个局部候选也未通过：压板、电源板、CAM板或后壳仍阻挡。这仅是被测曲线族失败，不是所有外绕方案不可能。

本研究建立了30×42×7轴承的独立参考，重新构造3件打印件，不缩放原轴承、不移动PCB或光学件。尺寸来源是[NSK6806ZZ官方页面]({sources[1]['url']})；原轴承依据[NSK6804ZZ官方页面]({sources[0]['url']})。官方目录标称质量分别24g和17g，增加7g仅指轴承，不是整机称重。完整滚道/防尘盖CAD、实测配合、价格及库存未确认。

## 局部通道结果

![固定座和轴颈的实体截面](local_sections.png)

- 三件打印实体各自连通；原D形反力孔壁、两条原承力连接及上部舵机座保留，指定保护区移除体积为0。
- 11根局部曲线在130个有限头部姿态下通过检查，包含209原零件、29对插包络及14根已有固定候选线。线间最小保守下界{gap:.3f}mm；最小采样弯曲半径19.144mm。这是几何结果，不是导线动态寿命验证。
- 四根信号线采用Alpha2841/7目录最大OD0.6604mm；另七根OD1.4224mm只是空间样本，未完成线材/端子选型，不可据此下单或压接。
- 上下端Z130/Z200仍是临时端点。不能与旧四线完整路线直接拼接，也没有生成可制作的裁线图。

## 整体复核未通过

![当前主模型与候选的真实运动截面](head_motion_sections.png)

- {v['distinct_pair_pose_checks']}个去重零件—姿态检查中出现{len(v['new_overlaps'])}条新增相交记录，涉及3对零件；这不是33种独立缺陷。
- 仰头25°时，新偏航支撑颈部碰Head_Rear。抬高2mm的防脱压板在部分仰头姿态碰后壳，下俯20°时碰前壳。红色为真实实体交集。
- 固定/转动限位首次采样接触在±63.75°，早于原定64–64.5°检查区间，需调整；正常±60°范围的限位本身未相交。
- C1的限位根部挡住了轴承装入，已判废；C2把限位根部移到轴承外侧，轴承装入通过。C2的压板侧装、成对落座、螺钉装入及2AF工具局部路径通过，但都是**无新增软线**的有限刚体检查，不能代表完整装配。
- 两处嵌件导孔外1.2mm环状材料探针检查通过；轴颈名义壁厚2.35mm。两者不是全件最小壁厚、承载、PA12变形或蠕变验证。

下一步需要连同头底部的运动空间一起解决。主模型、正式STL、动画以及硬件源文件保持，不提交此候选打样。

## 可复现文件

- C1/C2的8件独立实体分别保存在C1_*.npz和C2_*.npz；3件打印件、1个轴承边界及4个平移2mm的既有紧固件。没有新增零件。
- [C2构建](C2_build.json)、[完整有限检查](C2_verification.json)、[本轮摘要](review.json)、[厂家来源](sources/manifest.json)。
- Blender5.2.2LTS d13f752e3b9c，项目manifold；报告Python3.12.14。实际日志保存在本目录。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/build_candidate.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/build_candidate_v2.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/verify_candidate.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/collision_sections.py
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/build_review.py
```

仍待：完整线路/FFC、固定、带线装配、反力夹初装、真实配套端子/舵盘、最终质量和驱动预算。所有实物及打印验证均另列NOT_TESTED。
'''
(HERE/'README.md').write_text(readme)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · 跨颈通道整体复核</title><style>body{{margin:0;background:#f3f5f4;color:#233c35;font:16px/1.85 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 22px 65px}}h1{{font-size:30px;line-height:1.4}}a{{color:#146c53}}.note{{padding:18px;background:#fff0dc;border:1px solid #d9b16a}}figure{{margin:24px 0;background:white;border:1px solid #cad4ce}}img{{display:block;width:100%}}figcaption{{padding:14px}}td,th{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #cbd6cf}}table{{border-collapse:collapse;width:100%;background:white}}.links{{display:flex;flex-wrap:wrap;gap:16px}}</style>
<main><nav><a href="../index.html">到货前待办</a> · <a href="../../../index.html?revision=V1.2-M1.48#camera-cam">主模型M1.48</a></nav>
<h1>局部通道有进展，整机运动仍有冲突</h1>
<p class="note"><b>候选未采用，完整线束未完成。</b> 较大内孔轴承允许保留反力孔壁并放入11根局部导线；完整打印件复核后，发现支撑颈部和防脱压板碰头壳，尚不能应用。主模型、STL和动画保持M1.48。</p>
<figure><a href="head_motion_sections.png"><img src="head_motion_sections.png" alt="原模型与候选在仰头25度和下俯20度的实体截面，红色显示候选与头壳相交"></a><figcaption>蓝：偏航支撑；金色：防脱压板；紫：转动后的头壳；红：实体相交。截面来自当前模型和独立候选，点击看大图。</figcaption></figure>
<table><tr><th>检查</th><th>结果及限制</th></tr>
<tr><td>11根局部线共存</td><td>通过130个有限姿态。线间保守间隙下界{gap:.3f}mm；上下端尚未连接实际端口，七根较粗线尚未选型。</td></tr>
<tr><td>固定座与舵机座</td><td>指定原D形孔壁、两条承力连接、上部舵机座保留。三件打印实体连通；不等于强度通过。</td></tr>
<tr><td>装入与工具</td><td>轴承装入、压板侧装和落座、螺钉及工具局部路径通过。只检查刚体，完整带线装配未完成。</td></tr>
<tr><td>完整头部运动</td><td>未通过：偏航支撑碰后壳；压板碰前/后壳。限位首次采样接触±63.75°，也需回到原目标区间。</td></tr>
<tr><td>轴承尺寸参考</td><td><a href="{sources[1]['url']}">NSK6806ZZ</a>30×42×7，原6804ZZ20×32×7；只建厂家边界，未选购。轴承目录质量增加7g；整机预算仍未关闭。</td></tr></table>
<figure><a href="local_sections.png"><img src="local_sections.png" alt="反力固定座保留两个承力连接，导线通过左右窗口和扩大后的轴颈"></a><figcaption>这是通过局部检查的通道。头壳冲突未解决前，不据此批准结构或制作线束。</figcaption></figure>
<h2>到货前仍剩5类</h2><p>完整线束、反力夹初装、未定采购件及安装、厂家传动与插接资料、质量与驱动预算。机械与硬件输入仍有工作，不能表述为只等实物。</p>
<p class="links"><a href="README.md">完整范围和命令</a><a href="C2_verification.json">整体复核</a><a href="sources/manifest.json">厂家来源</a><a href="review.json">本轮状态</a><a href="delivery.json">交付校验</a><a href="../work_status.json">剩余清单</a></p>
<p>PROTOTYPE / UNVALIDATED · 无制造、采购或主模型替换。</p></main></html>'''
(HERE/'index.html').write_text(html)
print('REVIEW_BUILT',summary['status'],summary['conflict_pairs'])
