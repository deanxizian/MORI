"""Publish bounded negative diagnostics without changing the adopted assembly."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import html
import json

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
ROOT = A8.parents[3]
ORDER = A8 / 'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT = ORDER / 'body_fixed_CAM'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())
inputs = {}
records = {}
for name, script in [
    ('H01_preinstalled', 'screen_H01_preinstalled_route.py'),
    ('H04_preinstalled', 'screen_H04_preinstalled_route.py'),
    ('body_fixed_CAM', 'screen_CAM_body_fixed_installation.py'),
]:
    p = ORDER / name / 'screen.json'
    d = read(p)
    assert d['status'] == 'BLOCKED'
    assert d['script_sha256'] == sha(A8 / script)
    assert not d['main_applied'] and not d['manufacturing_release']
    for source, digest in d['protected_sources'].items():
        assert sha(ROOT / source) == digest, source
    for source, digest in d['source_files'].items():
        assert sha(ROOT / source) == digest, source
        inputs[source] = digest
    for path in [p, A8 / script]:
        inputs[str(path.relative_to(ROOT))] = sha(path)
    records[name] = d
h01 = records['H01_preinstalled']
h04 = records['H04_preinstalled']
fixed = records['body_fixed_CAM']
assert [r['counts']['controls'] for r in h01['rows']] == [821, 821]
assert len(h04['rows']) == 8
baseline = next(r for r in fixed['rows'] if r['stage'] == 'settled_baseline')
blocked = next(r for r in fixed['rows'] if r['stage'] == 'body_bridge_back')
assert baseline['status'] == 'PASS'
witness = blocked['failure']['minimum_sample_witness']
assert witness['intersection_witness'] and blocked['failure']['obstacle'] == 'Yaw_Base'
assert blocked['failure']['bridge_transform'][2][3] == 18
assert fixed['fixed_body_wires'] == 14 and fixed['CAM_wires'] == 4

body = '''# 身体线束装配：进一步诊断

## 已明确的范围

H02 的低位走向及提前连接候选仍然有效。本页检查接下来的 H01、H04，
并比较让 CAM 线束留在身体侧的不同装配思路。所有结果为独立候选，
使用前序研究中尚未采用的打印件；主模型 M1.47、PCB 和正式针序没有变动。

| 尝试 | 实际检查 | 结果 |
|---|---|---|
| H01 提前接好，CAM 随桥移动 | 每根 821 组前侧、后侧及侧向走向；每根 303 组通过静态初筛 | 这 303 组均未通过后续有限装配位置检查，障碍是移动的 CAM 导线；没有选出双线组合 |
| H04/IMU 提前接好，降低上部弯线 | 8 根导线各 106 组控制参数 | 只有第 1、8 根各自找到个别候选，其余未通过；通过静态初筛但装配失败的候选，障碍均为移动的 CAM PH 胶壳；未形成八线组合 |
| PH 胶壳和完整 CAM 线束留在身体侧，桥单独移动 | 保留 14 根身体线、4 根完整 CAM 线及 29 个插头空间分配 | 完全坐稳的基准通过；桥抬高 18 mm 的保存位置与 CAM 第 1 根导线相交，因此原桥路径不能直接套用 |

最后一项保留原有线长，头部端余线仍按前序候选竖直暂存，没有截短导线。
上移 0.5 mm 的首个保守间隙拒绝不能直接说成相交：该处最小采样表面间隙约 0.307 mm，
需要更细的间隙判断。另一个上移 18 mm 的位置则有明确的曲线采样相交证据，
足以否定这条既定的固定线形路径。轴承附近另有约 0.281 mm 的采样间隙，不满足 0.3 mm 名义要求。

## 接下来要完成的设计

不能继续把静态布线通过或裸插头能插入，称为完整带线装配完成。
需要使 CAM 的下端连接、穿桥部分和上方暂存线分阶段配合运动：先建立保持完整线长、
端部方向和最小弯曲半径的送线动作，再检查已有线束、桥、壳和轴承。
当前结果没有证明所有路线都不可能，也没有授权扩孔、改板或加零件。

## 厂家资料与项目设计的分界

- JST PH/SH 公共目录已取得，接头、端子和适用线规有来源。
- 本轮复查 JST 英国 SH 页面，专用手册、端子图和 STEP 都仍链接到日本官网邮件申请页；没有取得新增专用文件，也没有提交联系资料。
- 线长、分支位置和上述装配动作属于项目设计，仍未完成，不能归为只能等待实物。
- 制线方的实际压接工艺、首件和动态弯折验证，与本页名义几何检查分开。

[JST 英国 SH 页面](https://www.jst.co.uk/productSeries.php?pid=7929) ·
[专用端子图申请入口](https://www.jst-mfg.com/product/index.php?doc=4&filename=SSH-003T-P0.2-H.pdf&series=231&type=10) ·
[SHR-04V-S STEP 申请入口](https://www.jst-mfg.com/product/index.php?doc=2&filename=SHR-04V-S.zip&series=231&type=10)。

## 数据

[H01](../H01_preinstalled/screen.json) · [H04](../H04_preinstalled/screen.json) ·
[CAM 保持身体侧的检查](screen.json) · [H02 已通过的独立候选](../H02_preinstalled/index.html)。

未完成连续装配、人手/工具操作、完整端子入壳与固定，尚无供应商最终裁线图。
'''
(OUT / 'README.md').write_text(body)
table = ''.join('<tr><td>' + html.escape(name) + '</td><td>' + html.escape(result) + '</td></tr>'
                for name, result in [
    ('H01 提前接好', '每根 821 组；303 组通过静态初筛，均未通过现有 CAM 随桥移动的动作。'),
    ('H04 / IMU 提前接好', '每根 106 组；未形成八线组合，装配阶段的障碍是 CAM 的 PH 胶壳。'),
    ('CAM 留在身体侧，桥单独装入', '坐稳基准通过；桥上移 18 mm 时与导线相交。'),
])
(OUT / 'index.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 身体线束装配诊断</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:950px;margin:40px auto;padding:0 24px;background:#f5f7f6;color:#233c3c}}a{{color:#086879}}section{{background:white;padding:22px;margin:20px 0;border-radius:10px}}td,th{{text-align:left;border-bottom:1px solid #ccd8d5;padding:12px}}table{{border-collapse:collapse;width:100%}}.note{{background:#fff0dc}}</style>
<p><a href="../review/index.html">← 装配顺序</a></p><h1>身体线束：装得下，还要能装进去</h1>
<section class="note">独立诊断，主模型 M1.47 未改。H02 的已有候选保留；H01、IMU 和 CAM 的完整带线装配尚未闭合。</section>
<section><table><tr><th>尝试</th><th>结果</th></tr>{table}</table></section>
<section><h2>卡点已定位到装配动作</h2><p>CAM 随桥整体移动会碰到身体线束；保持 CAM 不动，既定桥路径又会穿过导线。下一步需要分段送线动作，并核对完整线长与弯曲半径。</p><p>这三项都是有限候选的结果，并不证明所有方案都不可行。没有据此改孔、改板、加零件或放行制造图。</p></section>
<section><h2>资料可以查，项目设计仍要完成</h2><p>JST 公共目录已取得。英国官网的 SH 专用资料链接仍指向需要邮件申请的日本官网页面，未取得新增专用图纸。线长、分支及装配动作仍由项目完成。</p><p><a href="https://www.jst.co.uk/productSeries.php?pid=7929">JST 官方资料入口</a> · <a href="README.md">详细范围与资料链接</a></p></section>
<p><a href="../H01_preinstalled/screen.json">H01 检查</a> · <a href="../H04_preinstalled/screen.json">IMU 检查</a> · <a href="screen.json">CAM 固定侧检查</a> · <a href="../H02_preinstalled/index.html">H02 候选</a> · <a href="publication.json">来源校验</a></p></html>''')
report = dict(status='PASS', scope='Publication of bounded negative assembly diagnostics only',
              generated_utc=datetime.now(timezone.utc).isoformat(),
              script_sha256=sha(SCRIPT), protected_sources=fixed['protected_sources'],
              source_files=inputs, H01_preinstalled='BLOCKED', H04_preinstalled='BLOCKED',
              body_fixed_CAM='BLOCKED', complete_assembly='BLOCKED',
              main_applied=False, manufacturing_release=False,
              outputs={name: sha(OUT / name) for name in ['README.md', 'index.html']})
(OUT / 'publication.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
state_path = A8.parent / 'work_status.json'
state = read(state_path)
state['CAM_body_order_diagnostics'] = dict(
    publication=str((OUT / 'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT / 'publication.json'),
    H01_preinstalled='BLOCKED', H04_preinstalled='BLOCKED', body_fixed_CAM='BLOCKED',
    H02_existing_candidate='PASS', complete_attached_assembly='BLOCKED',
    next_design='Segmented CAM feeding while preserving full length, terminal directions and bend radius',
    main_applied=False, manufacturing_release=False)
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
print('CAM_BODY_ORDER_DIAGNOSTICS_PUBLISHED; complete assembly BLOCKED')
