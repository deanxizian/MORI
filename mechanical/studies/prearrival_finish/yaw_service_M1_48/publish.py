"""Publish the independent four-wire study; do not alter robot geometry."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
FINISH = HERE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda name: json.loads((HERE / name).read_text())
motion = load('refined_adaptive_all.json')
packing = load('curve_packing_refined.json')
radius = load('radius_evidence.json')
sections = load('section_checks.json')
construction = load('refined_construction.json')
assert all(d['status'] == 'PASS' for d in [motion, packing, radius, sections, construction])
assert motion['source_main_sha256'] == sha(PROJECT / 'mechanical/mori_v1_2.blend')
assert len(motion['substituted_prints']) == 2
assert not motion['main_applied'] and motion['whole_harness'] == 'BLOCKED'
now = datetime.now(timezone.utc).isoformat()
gap = packing['minimum_pair_gap_lower_bound_mm']
oldwall = sections['walls']['Pitch_Yoke_native']['minimum']['thickness_mm']
newwall = sections['walls']['Pitch_Yoke']['minimum']['thickness_mm']

readme = f'''# M1.48：四根 CAM 连续路线与颈部通道候选

**四根 CAM 线从基板 J5 接到 CAM 出线预留位置的候选，通过本页列出的数字检查。
完整线束仍为 BLOCKED，两件通道候选尚未应用主模型。**

## 本次结果

- 直接读取 M1.48 的 209 件实体，仅以两个明确标识的独立通道候选替代 Yaw_Base、Pitch_Yoke。
- 检查包括 29 个对插包络和 14 根已有候选线；没有继承旧研究的实体间隙结论。
- 130 个组合姿态（偏航 −60° 至 +60°，俯仰 −20° 至 +25°）下，520 条线路与实体的名义间隙检查通过。
- 780 组线间检查、520 组非局部自接近检查通过。线间保守下界最小 {gap:.6f} mm，要求 0.3 mm；这个下界不是制造余量。
- 线径仍为 0.6604 mm。匹配到原数学曲线的最小名义弯曲半径 7 mm，要求 6.9342 mm；未验证线材实际形态和动态寿命。

![四根连续候选](complete_route.png)

图中部分实体隐藏以便观察；检查时仍包含它们。末端使用 CAM 出线位置预留，
插合面、端子和逻辑针位对应仍需接口资料确认。颜色仅区分机械路线。

## 两件通道的代价

| 项目 | 相对当前主模型 |
|---|---:|
| Yaw_Base 移除材料 | {construction['parts'][0]['removed_mm3']:.3f} mm³ |
| Pitch_Yoke 移除材料 | {construction['parts'][1]['removed_mm3']:.3f} mm³ |
| 新增打印件 / 紧固件 | 0 / 0 |
| 轴颈有限截面采样最薄壁 | {oldwall:.3f} → {newwall:.3f} mm |

没有带入历史候选的凸起固定座。两件均为单个连通实体，未检出零面积面或非二面边。
轴颈壁厚只检查了 17 个截面 × 720 个方向，不代表全部最小壁厚；不构成 PA12 强度结论。
局部网格存在很小的正面积三角形，尚未做候选制造导出放行。

![原件与候选通道剖面](channel_sections.png)

此前的零厚度残片和粗采样保守告警已单独诊断，未用调小线径、放宽间隙要求或排除两个打印件来取得当前通过结果。
早期失败文件保留为过程记录；当前结果以 refined_adaptive_all、curve_packing_refined、radius_evidence 和 section_checks 为准。

## 仍需做的工作

1. 线的固定、应力释放、端子与胶壳装入，以及当前候选的完整带线装配。
2. 另 7 根跨关节导线、相机与屏幕 FFC；与已有 14 根身体候选线合并复核。
3. 两个通道对承载、装入路径及可制造性的完整复核。结构方案需用户确认后才能应用主模型。
4. 实际插合视图、压接出线、线材与供应商工艺数据；到货后再验证装配、磨损和寿命。

曲线是规定的数学形态；长度一致不证明柔性导线会自然保持这条路径。
姿态是离散检查，不是全连续运动碰撞证明。没有发布裁线尺寸、采购或制造数据。
主模型仍是 M1.48，正式 STL 和装配动画保持已批准状态。

## 原始文件

- [独立可编辑 Blender](review.blend)
- [实体与姿态](refined_adaptive_all.json) · [四线同时排布](curve_packing_refined.json)
- [曲率与来源](radius_evidence.json) · [拓扑和截面](section_checks.json)
- [两个通道的实体差异](refined_construction.json)
- [发布与哈希](publication.json) · [交付核对](delivery.json)

更新时间：{now}
'''
(HERE / 'README.md').write_text(readme)

html = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI M1.48 · CAM 四线连续候选</title>
<style>body{{margin:0;background:#f3f5f4;color:#253c35;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1080px;margin:auto;padding:28px 22px 60px}}h1{{font-size:31px;line-height:1.35}}h2{{margin-top:32px}}a{{color:#176950}}.note{{padding:16px 20px;background:#fff1d4;border:1px solid #d9b46b}}figure{{margin:24px 0;background:white;border:1px solid #c7d2cc}}img{{display:block;width:100%}}figcaption{{padding:12px 16px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:12px;border-bottom:1px solid #ccd7d1;text-align:left;vertical-align:top}}.links{{display:flex;gap:16px;flex-wrap:wrap}}details{{border:1px solid #c7d2cc;padding:14px 18px;margin-top:24px}}@media(max-width:650px){{main{{padding:18px 12px}}h1{{font-size:25px}}}}</style>
<main><nav><a href="../index.html">到货前待办</a> · <a href="../../../index.html?revision=V1.2-M1.48#camera-cam">主模型 M1.48</a></nav>
<h1>四根 CAM 候选已接通，完整线束还未完成</h1>
<p class="note"><b>本次完成连续路线的数字检查。</b> 路线使用两件独立的颈部通道候选，尚未应用主模型。固定、带线装配、另 7 根跨关节线和 FFC 仍待完成，完整线束为 BLOCKED。</p>
<figure><img src="complete_route.png" alt="M1.48 内部的四根 CAM 连续候选线"><figcaption>从基板 J5 到 CAM 出线预留位置的四根候选。部分实体在图中隐藏，检查时仍包含；末端不是已经确认的实物插合模型。</figcaption></figure>
<h2>这次检查通过的范围</h2>
<table><thead><tr><th>检查</th><th>当前结果与范围</th></tr></thead><tbody>
<tr><td>实体间隙</td><td>PASS · 以当前 209 件实体为基础，仅替换两件候选；包含 29 个对插包络及 14 根已有候选线。</td></tr>
<tr><td>头部姿态</td><td>PASS · 偏航 −60°～+60°、俯仰 −20°～+25°，130 个组合姿态，共 520 条线路记录。</td></tr>
<tr><td>线间与自接近</td><td>PASS · 780 组线间、520 组非局部自接近检查；线间保守下界最小 {gap:.6f} mm，要求 0.3 mm。</td></tr>
<tr><td>弯曲半径</td><td>PASS · 匹配到原数学曲线的名义最小半径 7 mm，要求 6.9342 mm。未模拟导线弹性、磨损或寿命。</td></tr>
<tr><td>固定与整套装配</td><td>NOT_TESTED / BLOCKED · 当前候选的固定、端子装入和完整带线装配尚未完成。</td></tr>
</tbody></table>
<p>线径保持 0.6604 mm；检查没有调小线径或降低间隙要求。细化了粗采样不能判定的区间，仍保留曲线误差与数值余量。姿态本身是离散检查，不能据此保证全部连续运动。</p>
<h2>两件通道尚未批准</h2>
<p>Yaw_Base、Pitch_Yoke 分别移除约 {construction['parts'][0]['removed_mm3']:.1f}、{construction['parts'][1]['removed_mm3']:.1f} mm³ 材料。没有增加打印件、紧固件，也没有带入旧候选的凸起固定座。</p>
<p><b>轴颈采样最薄壁从 {oldwall:.2f} mm 降至 {newwall:.2f} mm。</b> 这是需要进一步复核的结构代价，不能仅凭导线放得下就采用。采样覆盖 17 个截面、各 720 个方向，不是全件壁厚或强度认证。</p>
<figure><img src="channel_sections.png" alt="两件颈部通道的原件与候选剖面，以及轴颈壁厚对比"><figcaption>红色表示相对主模型移除的材料。两件候选都是单个连通实体；制造导出和强度尚未放行。</figcaption></figure>
<h2>距离到货前工作完成，还剩五类</h2>
<table><thead><tr><th>类别</th><th>未完成内容</th></tr></thead><tbody>
<tr><td>完整线束</td><td>固定、应力释放、完整带线装配；另 7 根跨关节线与 FFC，最终裁线图。</td></tr>
<tr><td>反力夹初装</td><td>夹口薄边、工具与装入路径，需要结合最终舵盘接口完成。</td></tr>
<tr><td>采购件及安装</td><td>软轮胎定型，以及充电、制动部件与真实出线的安装和维护。</td></tr>
<tr><td>供应商接口资料</td><td>SCS0009 配套舵盘/轴/锁紧；S288 螺钉、WeAct 插接、CAM/FFC/压接配套资料。</td></tr>
<tr><td>质量与驱动预算</td><td>当前名义质量约 1.324 kg，高于 1.0～1.2 kg 工程目标，且完整线束等尚未计全。</td></tr>
</tbody></table>
<p>目前还不是“只等实物”。主模型仍为 M1.48；这次候选未进入正式 STL 或装配动画。插合包络与出线细节含估计，几何通过不等于实物装配合格。本页不提供供应商裁线尺寸。</p>
<p class="links"><a href="review.blend">独立 Blender</a><a href="upper_route.png">头部路线近景</a><a href="README.md">完整说明</a><a href="../work_status.json">完整状态记录</a></p>
<details><summary>原始检查与来源</summary><p class="links"><a href="refined_adaptive_all.json">实体与姿态</a><a href="curve_packing_refined.json">线间检查</a><a href="radius_evidence.json">曲率与来源</a><a href="section_checks.json">拓扑与壁厚</a><a href="refined_construction.json">实体差异</a><a href="publication.json">文件哈希</a><a href="delivery.json">交付核对</a></p><p>早期失败报告保留作为过程记录，当前结论以这五份报告为准。相同曲线的数学证据可复用，旧实体间隙结果没有直接沿用。</p></details>
</main></html>'''
(HERE / 'index.html').write_text(html)

detail = ('四根CAM线已在两个明确标识的颈部通道候选上，连续连接Motion J5至CAM出线预留位置；'
          '以M1.48当前209实体为基础，含29个对插包络、14根已有候选线，130姿态、线间与名义弯曲半径检查通过。'
          'Yaw_Base/Pitch_Yoke通道尚未采用，轴颈采样最薄壁由约2.25降至1.48mm，强度未验证。'
          '固定、应力释放、端子入壳、完整带线装配、另7根跨关节线/FFC及最终制作图仍未完成。'
          '原件外侧下部走线作为另一条有限候选保留，不能与本次内部通道混称。完整线束仍BLOCKED。')
changed = {}
for path, href in [(PROJECT / 'mechanical/index.html', 'studies/prearrival_finish/yaw_service_M1_48/index.html'),
                   (FINISH / 'index.html', 'yaw_service_M1_48/index.html')]:
    before = sha(path)
    text = path.read_text()
    block = f'<aside id="M1-48-yaw-service" class="notice"><b>四根CAM连续候选已通过数字检查，完整线束仍未完成。</b> 两件颈部通道尚未应用；固定、带线装配、另7根跨关节线和FFC待完成。<a href="{href}">查看最新路线、结构代价和五类剩余工作</a>。</aside>'
    if 'id="M1-48-yaw-service"' in text:
        text = re.sub(r'<aside id="M1-48-yaw-service".*?</aside>', block, text, count=1, flags=re.S)
    else:
        assert '<main>' in text
        text = text.replace('<main>', '<main>' + block, 1)
    text = text.replace('<b>四根身体至颈部候选已接通。</b>', '<b>早期外侧路线：仅身体至颈部。</b>')
    def replace_row(match):
        row = match.group(0)
        if '<td>完整线束</td>' not in row:
            return row
        cells = re.findall(r'<td>.*?</td>', row, re.S)
        assert len(cells) in (2, 3)
        cells[-1] = f'<td>{detail} <a href="{href}">当前依据</a></td>'
        return '<tr>' + ''.join(cells) + '</tr>'
    text = re.sub(r'<tr>.*?</tr>', replace_row, text, flags=re.S)
    path.write_text(text)
    changed[str(path.relative_to(PROJECT))] = dict(before=before, after=sha(path))

path = FINISH / 'work_status.json'
before = sha(path)
status = json.loads(path.read_text())
status['updated_utc'] = now
entry = next(x for x in status['remaining'] if x['id'] == 'harness')
entry['detail'] = detail
entry['latest_internal_channel_evidence'] = 'yaw_service_M1_48/index.html'
entry['latest_internal_channel_detail'] = detail
status['yaw_service_M1_48'] = dict(
    status='PASS', scope='Four complete mathematical CAM routes at finite poses, with two unadopted print cuts',
    evidence='yaw_service_M1_48/index.html', source_blend_sha256=motion['source_main_sha256'],
    native_parts=209, substituted_prints=['Yaw_Base', 'Pitch_Yoke'], mating_allocations=29,
    fixed_candidate_wires=14, head_poses=130, wire_pose_checks=520, mutual_checks=780,
    nonlocal_self_checks=520, minimum_pair_gap_lower_bound_mm=gap,
    minimum_nominal_radius_mm=radius['minimum_radius_lower_mm'],
    sampled_journal_wall_mm=dict(current=oldwall, candidate=newwall),
    retention='NOT_TESTED', full_assembly='NOT_TESTED', strength='NOT_TESTED',
    other_seven_wires_and_FFC='NOT_TESTED', main_applied=False, whole_harness='BLOCKED',
    supplier_cut_lengths_released=False, manufacturing_release=False)
path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
changed[str(path.relative_to(PROJECT))] = dict(before=before, after=sha(path))

commands = []
for script, log, args in [
    ('refine_neck_channels.py', 'refine_neck_channels.log', ''),
    ('replay_local_clearance.py', 'refined_adaptive_all.log', ' -- --refined --adaptive --all'),
    ('refine_curve_packing.py', 'curve_packing_refined.log', ''),
    ('check_sections.py', 'section_checks.log', ''),
    ('render_review.py', 'render_review.log', '')]:
    contents = (HERE / log).read_text()
    assert 'Blender quit' in contents and 'Traceback' not in contents, log
    commands.append(dict(
        reproduction_command='/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python ' + str((HERE / script).relative_to(PROJECT)) + args,
        cwd=str(PROJECT), log=log, log_sha256=sha(HERE / log), completion='Normal Blender completion recorded'))
pub = dict(
    status='PASS', scope='Publication of bounded candidate evidence; not whole-harness completion', utc=now,
    source_main_sha256=motion['source_main_sha256'], native_sources=motion['sources'],
    result_files=['refined_construction.json', 'refined_adaptive_all.json', 'curve_packing_refined.json', 'radius_evidence.json', 'section_checks.json'],
    reproduction_commands_and_completion_logs=commands,
    tools={'Blender': '5.2.2 LTS d13f752e3b9c', 'numpy_plot_runtime': 'mori-cad Python 3.12.14'},
    files={p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['publication.json', 'delivery.json']},
    changed_presentation_files=changed,
    geometry_scope='Independent two-print trial and four-wire preview only; main, hardware, STL and animation unchanged',
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False,
    historical_reports='Other screening/failure JSON files remain historical; not superseding the five result_files',
    limits=['Mating, crimp and CAM exit shapes contain allocations.', 'Candidate wall sample is not a strength check.',
            'Prescribed mathematical curves do not prove flexible-wire retention or assembly.',
            'No supplier wire cutting lengths released.'])
(HERE / 'publication.json').write_text(json.dumps(pub, ensure_ascii=False, indent=2) + '\n')
print('YAW_SERVICE_PUBLISHED', now, flush=True)
