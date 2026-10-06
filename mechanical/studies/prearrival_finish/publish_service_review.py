"""Plot actual M1.46 sections and publish the unresolved reaction-link assembly."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch, Patch
import numpy as np

HERE = Path(__file__).resolve().parent
M = HERE.parents[1]
report = json.loads((HERE / 'reaction_service_sections.json').read_text())
source = hashlib.sha256((M / 'mori_v1_2.blend').read_bytes()).hexdigest()
assert report['source_blend_sha256'] == source
equivalence = json.loads((HERE / 'interface_sync/source_equivalence.json').read_text())
assert equivalence['status'] == 'PASS' and equivalence['current_source_blend_sha256'] == source
assert not equivalence['changed_objects'] and not equivalence['embedded_animation_source_differences']
bench = json.loads((HERE / 'reaction_bench_order.json').read_text())
refined = json.loads((HERE / 'reaction_refined_path.json').read_text())
for checked in (bench, refined):
    assert checked['source_blend_sha256'] == equivalence['original_source_blend_sha256']
    assert checked['status'] == 'BLOCKED' and not checked['main_applied']
assert not bench['usable_delayed_fastening_angles_deg']
assert len(bench['orientation_checks']) == 180 and len(bench['bench_fastener_orders']) == 37
assert len(refined['results']) == 2
assert all(x['tested_states'] == 1820 and x['maximum_reached_lift_mm'] == 1.5 for x in refined['results'])
local_candidate = json.loads((HERE / 'reaction_access_candidate/screening.json').read_text())
assert local_candidate['source_blend_sha256'] == source
assert local_candidate['status'] == 'FAIL' and not local_candidate['main_applied']
assert local_candidate['source_unchanged']
palette = {'yoke': '#718389', 'link': '#398575', 'screw': '#e1a557',
           'tool': '#f4ce87', 'intersection': '#d54444'}
fig, axes = plt.subplots(1, 2, figsize=(12, 8))
for ax, row in zip(axes, report['sections']):
    for name, polygons in row['layers'].items():
        vertices, codes = [], []
        for poly in polygons:
            pts = np.asarray(poly)
            if len(pts) < 3:
                continue
            vertices.extend(pts.tolist() + [pts[0].tolist()])
            codes.extend([PlotPath.MOVETO] + [PlotPath.LINETO] * (len(pts)-1) + [PlotPath.CLOSEPOLY])
        if vertices:
            ax.add_patch(PathPatch(PlotPath(vertices, codes), facecolor=palette[name],
                                   edgecolor='#253e3c', linewidth=.8))
    if row['id'] == 'clamp_tool':
        ax.set_xlim(-20, 35); ax.set_ylim(184, 215)
        ax.set_title('A. Driver access at the assembled clamp\nX = 7 mm; provisional tool diameter 2.5 mm')
        ax.text(.02, -.17, 'Red: tool / yoke overlap, 9.26 mm³\nThis straight tool approach fails.', transform=ax.transAxes,
                va='top', fontsize=10)
    else:
        ax.set_xlim(-25, 25); ax.set_ylim(136, 220)
        ax.set_title('B. Preassembled link lifted by 2 mm\nX = 0 mm; bare yoke on the bench')
        ax.text(.02, -.09, 'Red: link / yoke overlap, 18.13 mm³\nThis straight insertion / removal approach fails.', transform=ax.transAxes,
                va='top', fontsize=10)
    ax.set_aspect('equal'); ax.grid(alpha=.18)
    ax.set_xlabel('Y (mm)'); ax.set_ylabel('Z (mm)')
fig.suptitle('M1.46 reaction-link assembly: two unresolved approaches', fontsize=17)
fig.legend(handles=[Patch(facecolor=palette[k], label=v) for k, v in [
    ('yoke', 'Existing Pitch_Yoke'), ('link', 'Reaction link'),
    ('tool', 'Screw / tool'), ('intersection', 'Solid overlap')]],
    loc='lower center', ncol=4, bbox_to_anchor=(.5,.025), frameon=False)
fig.text(.5,.015,'Unmodified main model · finite geometry checks · final SCS0009 horn/shaft not selected',
         ha='center', fontsize=9)
fig.tight_layout(rect=(0,.11,1,.94), w_pad=3)
out = HERE / 'reaction_assembly_review.png'
fig.savefig(out, dpi=160); plt.close(fig)

page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · 反力夹口装配未闭合</title><style>body{font:16px/1.85 system-ui,sans-serif;background:#edf1f0;color:#243a33;margin:0}main{max-width:1160px;margin:auto;padding:30px 24px 70px}a{color:#146c53}img{width:100%;background:white;border:1px solid #c6d2cc;border-radius:8px}.notice{padding:18px;background:#fff0d3;border:1px solid #dec59d;border-radius:9px}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #c4d1c9;text-align:left;vertical-align:top}code{word-break:break-all}</style><main>
<a href="index.html">到货前剩余工作</a><h1>反力夹口的初次装配仍未闭合</h1>
<p class="notice">当前 M1.46 主模型已复现这处阻挡；三处薄边候选没有解决它。已测试的直线装入和夹口工具路线 FAIL。有限倾斜搜索也尚未找到可行路径，因此当前不能把头部传动连接描述为可完整装配。</p>
<p>问题发生在固定的 Yaw_Reaction_Link 与旋转的 Pitch_Yoke 之间。完整头座从身体上拆下的路线可以通过，但这不说明最初能把反力件与头座装在一起；两项检查的前提不同。</p>
<img src="reaction_assembly_review.png" alt="当前主模型真实实体剖面：左为夹口螺钉工具受头座阻挡，右为预装反力件上移2毫米时与头座相交；红色为相交部分">
<h2>检查结果与范围</h2><table><tr><th>项目</th><th>结果</th></tr>
<tr><td>夹口已在头座内，再装横向螺钉/螺母</td><td>FAIL：测试的装入轴线被 Pitch_Yoke 挡住。</td></tr>
<tr><td>直柄工具伸入夹口</td><td>FAIL：直径2.5 × 30 mm预留工具与头座相交约9.26 mm³；最终螺钉驱动头和工具仍未选定。</td></tr>
<tr><td>先预装夹口，再从上方放入裸头座</td><td>FAIL：主模型直线上移2 mm已相交约18.13 mm³；反向装入经过相同位置。</td></tr>
<tr><td>主模型倾斜装入搜索</td><td>BLOCKED：已测试216组单轴倾斜/抬升组合，没有找到完整路径；不构成所有六自由度路线不可能的证明。</td></tr>
<tr><td>离机后旋转夹口，再装紧固件</td><td>BLOCKED：在不装轴承、舵机和身体的裸头座中，以2°间隔检查整圈相对旋转；再在37个方向检查后装螺钉/螺母、工具与回转路径，未找到可用顺序。螺钉轴向退出4.75mm即遇到环壁。</td></tr>
<tr><td>更细的组合穿入搜索</td><td>BLOCKED：裸反力件与预装总成分别测试1820个状态，平移和倾斜网格为0.25mm／0.25°，含组合移动；保持0.15mm采样间隙时最多仅抬升1.5mm，未穿出头座。仍是有限局部搜索，不排除尚未测试的其他六自由度路径。</td></tr>
<tr><td>薄边候选的附加搜索</td><td>改变Yaw角的紧固空间、平移与倾斜组合搜索均未闭合。没有为绕过失败而切槽、改变硬件尺寸或豁免碰撞。</td></tr>
<tr><td>局部夹口改形候选 C1</td><td>FAIL，未应用：后侧削平到Y−9mm、试配螺钉轴向上移1mm并外移0.6mm，直柄工具可达，130姿态未见新增运动干涉；但预装夹口上移1.75–13mm期间仍撞后侧舵机安装座。不能据工具检查通过就应用。</td></tr>
<tr><td>轮驱底盖及头身防脱压板</td><td>各自声明范围的拆装、工具、运动几何检查 PASS；不覆盖此反力件初装问题。</td></tr></table>
<h2>下一步</h2><p>按已确认的方向继续保留 SCS0009。需拿到匹配舵盘及紧固界面的资料，再一起确定反力件连接、穿入方向与工具路线；厂家资料可以在实物到货前索取。若需要改变打印件连接方式，会先给出具体候选和装配检查，再请用户确认。</p>
<p>为什么没有继续削小夹口：现有后侧耳座最前缘约Y−6.15mm；若直线装入留0.3mm名义间隙，夹口需退到Y−5.85mm。相对当前半径5.2mm的舵盘座，下部中心线处只余约0.65mm，且会切开半径6.4mm的上部让位孔。这会改变夹持结构，不是无功能凸起。该判断只针对当前占位舵盘，不是实物尺寸或强度结论。现有试配螺母还有约0.00847mm³的源模型微小重叠，候选未扩大该重叠，也没有按无碰撞豁免。</p>
<p>三处薄边候选的局部厚度和130姿态检查仍有效，但不足以证明完整装配。现有 M1.46-A1 动画将这部分按已预装总成演示，不能作为反力夹口初装验证。</p>
<p>此次同步机械接口文档后重建了主文件，全部216个源对象的几何、位置和显示属性保持一致。此前搜索报告保留计算时的源文件哈希，通过<a href="interface_sync/source_equivalence.json">严格等价记录</a>关联当前模型；没有把旧报告改写成重新运行过。</p>
<p><a href="reaction_service_sections.json">主模型剖面数据</a> · <a href="reaction_link_entry_baseline.json">主模型216组搜索</a> · <a href="reaction_bench_order.json">离机整圈旋转及后装紧固件</a> · <a href="reaction_refined_path.json">0.25mm组合穿入搜索</a> · <a href="reaction_access_candidate/screening.json">局部改形C1失败记录</a> · <a href="reaction_access_candidate/diagnostics.json">C1碰撞位置与剩余材料</a> · <a href="thin_candidate_service.json">候选拆装检查</a> · <a href="reaction_clamp_access.json">Yaw工具搜索</a> · <a href="reaction_link_path_search.json">组合路径搜索</a> · <a href="SUPPLIER_DATA_REQUEST.md">厂家问题单</a></p>
<p>主模型SHA256：<code>__SOURCE__</code></p><p>PROTOTYPE / UNVALIDATED · 模型、STL、硬件源文件均未因本次检查修改。</p></main></html>'''
(HERE / 'reaction_assembly_review.html').write_text(page.replace('__SOURCE__', source))
(HERE / 'reaction_assembly_images.json').write_text(json.dumps({
    'source_blend_sha256': source, 'source_unchanged': True, 'image': out.name,
    'image_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'data': 'reaction_service_sections.json',
    'additional_reports': ['reaction_bench_order.json', 'reaction_refined_path.json',
                           'reaction_access_candidate/screening.json', 'reaction_access_candidate/diagnostics.json'],
    'source_equivalence': 'interface_sync/source_equivalence.json'}, indent=2) + '\n')
print('Published reaction_assembly_review.html and exact section image')
