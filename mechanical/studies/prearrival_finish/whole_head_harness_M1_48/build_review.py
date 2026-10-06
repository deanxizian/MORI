"""Build the support-review figures and readable, explicitly unadopted record."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
HERE=Path(__file__).resolve().parent
load=lambda n:json.loads((HERE/n).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
new=load('section_checks.json');old=load('section_checks_four_line.json')
sections=load('sections.json');old_sections=load('sections_four_line.json')
pack=load('packing.json');outside=load('outside_bearing_screen.json')
assert new['source_main_sha256']==old['source_main_sha256']==pack['source_main_sha256']==outside['source_main_sha256']
assert new['script_sha256']==old['script_sha256']==sha(HERE/'check_host_sections.py')

def fill(ax,polygons,color,zorder):
    vv=[];cc=[]
    for p in polygons:
        vv.extend(p+[p[0]])
        cc.extend([MPath.MOVETO]+[MPath.LINETO]*(len(p)-1)+[MPath.CLOSEPOLY])
    if vv:ax.add_patch(PathPatch(MPath(vv,cc),facecolor=color,edgecolor='none',zorder=zorder))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,3,figsize=(12,8.6),sharex=True,sharey=True)
for row,z in enumerate([141.,146.]):
    for col,(title,data,variant) in enumerate([
        ('Current main M1.48',sections,'Yaw_Base_native'),
        ('Earlier 4-wire channel',old_sections,'Yaw_Base'),
        ('New 11-wire channel',sections,'Yaw_Base')]):
        ax=axes[row,col];s=data['Z'+str(z)]
        fill(ax,s['Yaw_Base_native'],'#d95335' if col else '#9eb2ad',1)
        if col:fill(ax,s[variant],'#9eb2ad',2)
        fill(ax,s['Yaw_Reaction_Link'],'#263f3a',3)
        fill(ax,s['Yaw_Reaction_Retainer_Screw'],'#d0c4a4',4)
        fill(ax,s['Yaw_Reaction_Retainer_Nut'],'#d0c4a4',4)
        ax.set_aspect('equal');ax.set_xlim(-10,10);ax.set_ylim(-10,10)
        ax.set_xticks([-8,0,8]);ax.set_yticks([-8,0,8]);ax.set_facecolor('#fafbf9')
        ax.set_title(title if row==0 else '')
        if col==0:ax.set_ylabel(f'Z = {z:g} mm\nY (mm)')
        if row==1:ax.set_xlabel('X (mm)')
        ax.text(.02,.02,'TOP SECTION',transform=ax.transAxes,fontsize=8,color='#51605a')
fig.suptitle('Reaction socket: channel cuts need redesign',fontsize=20,y=.97)
fig.legend(handles=[Patch(color='#9eb2ad',label='Remaining print'),Patch(color='#d95335',label='Removed material'),
    Patch(color='#263f3a',label='Fixed reaction stem'),Patch(color='#d0c4a4',label='Fasteners')],
    loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,.02))
fig.subplots_adjust(top=.9,bottom=.12,hspace=.14,wspace=.12)
fig.savefig(HERE/'socket_comparison.png',dpi=170,facecolor='white')
fig.savefig(HERE/'socket_comparison.svg',facecolor='white');plt.close(fig)

def at(report,z):return next(r for r in report['socket_contact'] if r['z_mm']==z)
oldz,newz=at(old,146.),at(new,146.)
oldwall=old['journal_walls']['Pitch_Yoke']['minimum']['thickness_mm']
newwall=new['journal_walls']['Pitch_Yoke']['minimum']['thickness_mm']
nativewall=new['journal_walls']['Pitch_Yoke_native']['minimum']['thickness_mm']
pairgap=min(r['surface_gap_lower_bound_mm'] for r in pack['selected_pairs']) if pack['selected_pairs'] and 'surface_gap_lower_bound_mm' in pack['selected_pairs'][0] else None
summary=dict(status='BLOCKED',scope='Unadopted routing and support review, not manufacturing release',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_main_sha256=new['source_main_sha256'],
    eleven_local_paths=pack['status'],eleven_channel_support='BLOCKED',
    previous_four_line_channel_support='BLOCKED',outside_bearing_screen=outside['status'],
    native_socket_reference_rays_Z146=oldz['original_contact_rays'],
    lost_socket_contact_rays_Z146={'four_line':oldz['lost_contact_rays'],'eleven_line':newz['lost_contact_rays']},
    journal_wall_samples_mm={'native':nativewall,'four_line':oldwall,'eleven_line':newwall},
    main_applied=False,main_geometry_changed=False,whole_harness='BLOCKED',manufacturing_release=False,
    next_work='Choose separate corridors and place the flexible section clear of the keeper; preserve reaction socket and bearing support before endpoint and assembly work.',
    evidence={n:sha(HERE/n) for n in ['packing.json','host_cuts.json','section_checks.json','section_checks_four_line.json','outside_bearing_screen.json']})
(HERE/'review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

readme=f'''# M1.48 十一根跨颈导线：通道支座复核

当前状态：**BLOCKED，候选未采用，主模型未修改**。

## 新得到的结果

- 同时排下 11 根局部数学曲线：4 根信号线使用 Alpha 2841/7 目录最大线径 0.6604 mm；另 7 根使用 1.4224 mm 空间预留。后者不是已选线材，不能直接接到要求更细绝缘外径的 GH 端子，也不能据此发布线材采购单。
- 209 件当前零件为基础，包含 29 个插头包络、14 根固定候选线；先排除两件明确命名的通道宿主进行 130 姿态筛查，再构建两件通道单独重查。
- 导线共存、间隙和名义曲率通过相应有限检查；上下端 Z130/Z200 是临时截断位置，尚未连接到各接口。四根信号线的中段也改了，不能与上一版完整 CAM 路线直接拼接。
- 支座复核未通过：新的通道切穿了反力轴 D 形固定座的部分孔壁，并留下两个微小悬空残片。
- 已补查之前的四线通道：固定座顶部也出现孔壁局部开口。此前的路线、轴颈及局部装配 PASS 没有覆盖这项，不能据此放行固定座。

## 截面依据

![反力轴固定座截面对比](socket_comparison.png)

Z146 截面原始孔壁的 {oldz['original_contact_rays']} 条有效径向样本中，四线候选有 {oldz['lost_contact_rays']} 条、十一线候选有 {newz['lost_contact_rays']} 条的原孔壁被新增开口取代。这是几何截面的采样统计，不是承载能力下降比例，也没有把边界尖端的径向宽度冒充全件最小壁厚。

轴颈 17 个截面 × 720 方向的最薄样本：原件 {nativewall:.3f} mm、四线候选 {oldwall:.3f} mm、十一线候选 {newwall:.3f} mm。轴颈还存在材料，不能消除下方反力固定座的问题；强度和打印配合均未验证。

## 外绕的第一轮检查

尝试 R19.5 / R20.5、Z120–195 的局部定长曲线，同时保留两件宿主 R18 内的全部原始材料。288 条候选没有找到通过者：236 条首先碰到防脱压板，52 条首先碰到电源板。没有忽略、缩小或切开这些硬件来取得通过。这只是两组曲线族失败，不证明全部外绕路线不可行。

下一步将转动余量段移到防脱压板上方并分开通道，先保住反力固定座与轴承支撑，再接通两端、设计固定和检查装配。还没有可供用户批准的通道方案。

## 命令与边界

Blender 5.2.2 LTS，Python 3.13，使用项目已有 manifold。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/screen_neck.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/pack_neck.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/inspect_host_cuts.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/check_host_sections.py
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/check_host_sections.py -- --four-line
/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/screen_outside_bearing.py
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/whole_head_harness_M1_48/build_review.py
```

实际日志分别保存于 screen.log、packing.log、host_cuts.log、sections.log、sections_four_line.log、outside_bearing_screen.log、build_review.log。结果中的 SOURCE SHA 指向 M1.48 当前主模型。旧研究的初始化代码没有执行；旧四线候选仅按已声明 NPZ 载入比较。

真实线材、动态寿命、完整端子/尾线、固定、连续运动、完整装配和最终裁线图仍未完成。硬件源、主模型、正式 STL 和视频保持不变；主版本仍为 M1.48 / 动画 M1.48-A1。
'''
(HERE/'README.md').write_text(readme)

html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI M1.48 · 跨颈线束与固定座复核</title><style>body{{margin:0;background:#f3f5f4;color:#233c35;font:16px/1.85 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1100px;margin:auto;padding:26px 22px 65px}}h1{{font-size:30px;line-height:1.4}}a{{color:#146c53}}.note{{padding:18px;background:#fff0dc;border:1px solid #d9b16a}}figure{{margin:24px 0;background:white;border:1px solid #cad4ce}}img{{display:block;width:100%}}figcaption{{padding:14px}}td,th{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #cbd6cf}}table{{border-collapse:collapse;width:100%;background:white}}.links{{display:flex;flex-wrap:wrap;gap:15px}}</style>
<main><nav><a href="../index.html">到货前待办</a> · <a href="../../../index.html?revision=V1.2-M1.48#camera-cam">主模型 M1.48</a></nav>
<h1>集中穿颈会损伤固定座，通道需要重做</h1>
<p class="note"><b>这两种通道均未采用。</b> 新的 11 线方案虽通过局部线路筛查，但会切穿反力固定座的孔壁。补查发现，之前的四线候选在固定座顶部也有同类问题。主模型和正式打印文件没有带入这些通道。</p>
<figure><a href="socket_comparison.png"><img src="socket_comparison.png" alt="原固定座、旧四线通道和新十一线通道在两个高度的真实截面对比，红色为移除材料"></a><figcaption>灰绿是保留的打印材料，深绿是固定反力轴，红色是通道移除的材料。点击查看大图。固定座顶部原孔壁被局部切开，不能仅依据导线间隙检查放行。</figcaption></figure>
<table><tr><th>检查对象</th><th>本轮结果</th></tr>
<tr><td>11 根局部路线</td><td>130 姿态及线间检查通过；仅上下临时截面之间，未接至所有接口。4 根按 0.6604 mm，另 7 根按 1.4224 mm 预留，后者尚未选型。</td></tr>
<tr><td>新通道的支座</td><td>BLOCKED：反力固定座部分孔壁被切穿，且出现两个微小悬空残片。</td></tr>
<tr><td>之前的四线通道</td><td>BLOCKED：此次补查发现固定座顶部也有孔壁开口。此前路线与轴颈的检查结果不能替代本项。</td></tr>
<tr><td>轴承轴颈</td><td>采样最薄壁：原件 {nativewall:.2f} mm、四线 {oldwall:.2f} mm、11 线 {newwall:.2f} mm。该局部结果不解决固定座问题，也不证明强度。</td></tr>
<tr><td>外绕第一轮</td><td>保留中心 R18 内的原始材料后，288 条局部候选仍未通过，主要碰到防脱压板，另有电源板冲突。仅这两组曲线族失败。</td></tr></table>
<h2>接下来要完成什么</h2><p>分开通道，把转动余量段放到防脱压板上方；先保护固定座和轴承支撑，再完成端部连接、固定、带线装配和供应商制作图。目前没有可直接应用的通道候选。</p>
<p>到货前的剩余工作仍为五类：<b>完整线束、反力夹初装、未定采购件及安装、厂家接口资料、最终质量与驱动复核</b>。部分工作依赖厂家或硬件输入；还不是只等实物验证。</p>
<p class="links"><a href="README.md">完整范围与命令</a><a href="review.json">本轮状态</a><a href="section_checks.json">11 线支座</a><a href="section_checks_four_line.json">四线支座补查</a><a href="outside_bearing_screen.json">外绕筛查</a><a href="delivery.json">来源与交付核对</a><a href="../work_status.json">全部剩余工作</a></p>
<p>PROTOTYPE / UNVALIDATED · 主模型 M1.48、STL 和装配视频保持；无制造或采购放行。</p></main></html>'''
(HERE/'index.html').write_text(html)
print('REVIEW_BUILT',json.dumps(summary,ensure_ascii=False))
