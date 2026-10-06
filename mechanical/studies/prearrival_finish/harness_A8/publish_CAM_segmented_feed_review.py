"""Publish finite configuration progress and the actual unresolved feed stage."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,html

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'feed_pose_packing'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
sources={}
records={}


def receive(path,script):
    d=read(path)
    assert d['script_sha256']==sha(A8/script),path
    assert not d['main_applied']
    for key in ['source_files','protected_sources']:
        for p,digest in d.get(key,{}).items():assert sha(ROOT/p)==digest,p
    for p in [path,A8/script]:sources[str(p.relative_to(ROOT))]=sha(p)
    sources.update(d.get('source_files',{}))
    return d


for label in ['lift18','rear14_lift18']:
    d=receive(OUT/label/'screen.json','screen_CAM_feed_pose_packing.py')
    v=receive(OUT/label/'verification.json','verify_CAM_feed_pose_packing.py')
    assert d['status']==v['status']=='PASS'
    assert v['screen_sha256']==sha(OUT/label/'screen.json')
    assert v['curves_sha256']==d['curves_sha256']==sha(OUT/label/'curves.npz')
    assert len(v['selected_checks'])==4 and len(v['selected_pairs'])==6
    assert len(v['terminal_pairs'])==6 and len(v['terminal_other_wire_checks'])==12
    assert all(r['self_check']['status']==r['terminal_check']['status']=='PASS' for r in v['selected_checks'])
    records[label]=v
    sources[str((OUT/label/'curves.npz').relative_to(ROOT))]=sha(OUT/label/'curves.npz')
for name,script in [
    ('feed_lift_transition','screen_CAM_feed_lift_transition.py'),
    ('feed_lift_schedule','screen_CAM_feed_lift_schedule.py'),
    ('feed_lift_refinement','refine_CAM_feed_lift_schedule.py'),
    ('feed_lift_pulse','screen_CAM_feed_lift_vertical_pulse.py'),
]:
    records[name]=receive(ORDER/name/'screen.json',script)
for name in ['feed_lift_transition','feed_lift_schedule','feed_lift_refinement']:
    assert records[name]['status']=='BLOCKED'
refined=records['feed_lift_refinement']
assert len(refined['results'])==6
witnesses=[r['failure']['minimum_sample_witness'] for r in refined['results']]
assert sum(r['intersection_witness'] for r in witnesses)==3
assert all(r['margin_violation_witness'] for r in witnesses)
projection=receive(OUT/'projections.json','extract_CAM_feed_pose_review.py')
plot=receive(OUT/'plot.json','plot_CAM_feed_pose_review.py')
assert projection['status']==plot['status']=='PASS'
assert plot['outputs']['comparison.png']==sha(OUT/'comparison.png')
protected=records['lift18']['protected_sources']
pulse=records['feed_lift_pulse']
printed=', '.join(pulse['source_prints'])
if pulse['status']=='PASS':
    pulse_sentence='临时降低中段后，找到四根线同时通过 37 个有限抬升位置的组合；连续过程以及继续后移、升到装配高度仍未验证。'
else:
    pulse_sentence='又检查了临时降低中段 0.5–4 mm 的 7 组动作，仍未形成四根线同时通过的抬升组合。'
gaps={label:min(r['surface_gap_lower_bound_mm'] for r in records[label]['selected_pairs']) for label in ['lift18','rear14_lift18']}
body=f'''# CAM 分段送线：配置有解，装配动作还没完成

## 本轮实际完成

保持身体端 PH 接口不动，保留 14 根身体线（包括已通过的低位 H02），在两个明确位置分别找到四根 CAM 线的排布。

| 独立位置 | 已检查 | 四线之间最小保守间隙 |
|---|---|---|
| 桥上移 18 mm | 四线对当前阶段零件/插头/身体线、自绕、端子占位、六对线及六对端子和十二项端子对他线 | {gaps['lift18']:.3f} mm |
| 同样上移 18 mm，再向后移 14 mm | 同上；身体端胶壳不动 | {gaps['rear14_lift18']:.3f} mm |

两处都保留完整的原名义线长，用上方暂存余线补偿下部路线变化。身体端前 5 mm 直段保留；解析圆弯最小半径为 7 mm。
端子是明确标注的 1×1.8×4.1 mm 空间分配，并非实际成品端子的完整厂家模型。

![两个独立排布的投影](comparison.png)

图中包含零件真实投影，不是装配动作连续帧。为便于观察，画框截去了上部暂存余线；计算没有截短导线。

## 仍未完成的具体动作

从坐稳位置开始，每 0.5 mm 检查一次桥上抬，共 37 个位置；保持原弯线形式，避免在独立方案之间突然换圈。
第 1–3 根各自有通过这段有限位置的候选；第 4 根的原形式在中途靠近 H02，未形成四线组合。

调整第 4 根收弯时机的 6 组候选仍未通过。已保留原解析误差，将线段细分到最大 0.015 mm 复核：
三组有明确模型相交证据，其余三组最小采样间隙约 0.170、0.260、0.279 mm，小于 0.3 mm 名义要求。
不能把所有保守拒绝都说成相撞，也不能把两个端点放得下说成中间能装过去。

{pulse_sentence}

这些是所测试动作的结果，不证明所有布线和装法都不可行。下一步需要调整第 4 根与 H02 的相对走向或分段动作，并验证前后工序的同一份导线。

## 范围和保留项

- 研究使用已有未采用的打印候选：{printed}。没有据此修改主模型 M1.47、PCB 或针序。
- 全部 209 件原始模型中，本身体阶段装入 122 件；偏航/俯仰头组按工序暂不装。29 个插头空间分配保留。
- 主装配视频保持；不得把独立排布图替代完整装配验证。
- H01/H04、其余跨关节线、FPC、端子入壳、扎带、人手和供应商最终裁线图仍需完成。
- 已取得的公共厂家资料继续有效。上面的路线和工序属于项目设计，不能归为等待实物。

## 可复核文件

[抬高位置](lift18/verification.json) · [后移位置](rear14_lift18/verification.json) ·
[逐步抬升](../feed_lift_transition/screen.json) · [收弯时序](../feed_lift_schedule/screen.json) ·
[间隙细化](../feed_lift_refinement/screen.json) · [临时降低中段](../feed_lift_pulse/screen.json) ·
[来源和保护文件](publication.json)。

本页发布检查通过，只表示结果、来源和页面一致。完整线束及制造图状态仍为 BLOCKED。
'''
(OUT/'README.md').write_text(body)
(OUT/'index.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · CAM 分段送线复核</title><style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#233c3c;background:#f5f7f6;max-width:1120px;margin:32px auto;padding:0 24px 50px}}a{{color:#086879}}section{{background:#fff;border-radius:10px;padding:22px;margin:20px 0}}.note{{background:#fff0dc}}img{{display:block;width:100%;height:auto}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #d3dfde}}table{{width:100%;border-collapse:collapse}}</style>
<p><a href="../body_fixed_CAM/index.html">← 上次装配诊断</a> · <a href="../../../../../../../../../supplier_source_update/index.html">资料与设计进度</a></p>
<h1>四根 CAM 线：位置放得下，移动过程还要解决</h1>
<section class="note"><p>两个中间位置已有独立排布通过几何检查；从坐稳位置到这些位置的完整送线动作仍未通过。主模型 M1.47 未改，制造图未放行。</p></section>
<section><h2>已找到两处排布</h2><table><tr><th>桥的位置</th><th>四线最小保守间隙</th><th>结果范围</th></tr>
<tr><td>上移 18 mm</td><td>{gaps['lift18']:.3f} mm</td><td>单个位置的零件、邻线、自绕和端子空间</td></tr>
<tr><td>上移 18 mm、后移 14 mm</td><td>{gaps['rear14_lift18']:.3f} mm</td><td>同上，身体端 PH 接口保持不动</td></tr></table>
<p>完整线长保留，身体端直段保留，解析圆弯最小半径 7 mm。端子仍是明确标注的尺寸分配。</p>
<a href="comparison.png"><img src="comparison.png" alt="坐稳基准及两处独立CAM排布的正面和侧面投影；不是连续装配动画"></a></section>
<section><h2>第 4 根线卡在中间动作</h2><p>保持原弯线形式，每 0.5 mm 逐步抬升。第 1–3 根各自有候选，第 4 根尚未与它们形成完整组合。改变收弯时机的六组尝试，在细化到 0.015 mm 线段后，仍有 H02 间隙不足或明确相交。</p><p>{html.escape(pulse_sentence)}</p><p>这需要继续完成线束设计；没有据此扩大孔、移动 PCB 或增加零件。</p></section>
<section><h2>验证范围</h2><p>14 根身体线、当前阶段 122 件原模型零件、29 个插头空间分配保留。使用前序研究的未采用打印候选。其余跨关节线、FPC、扎带、人手、真实端子入壳和最终裁线尺寸仍待完成。</p><p><a href="README.md">完整说明</a> · <a href="lift18/verification.json">位置一</a> · <a href="rear14_lift18/verification.json">位置二</a> · <a href="../feed_lift_refinement/screen.json">细化失败证据</a> · <a href="../feed_lift_pulse/screen.json">临时降低中段</a> · <a href="publication.json">来源校验</a></p></section></html>''')
report=dict(status='PASS',scope='Publication of verified independent configurations and finite-transition diagnostics',
            generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
            source_files=sources,protected_sources=protected,
            verified_single_poses=2,single_pose_geometry='PASS',
            single_pose_minimum_pair_gaps_mm=gaps,
            lift_transition='BLOCKED',lift_timing='BLOCKED',lift_refinement='BLOCKED',
            temporary_lowering=pulse['status'],complete_attached_assembly='BLOCKED',
            continuous_movement='NOT_TESTED',main_applied=False,manufacturing_release=False,
            outputs={name:sha(OUT/name) for name in ['README.md','index.html','comparison.png','plot.json','projections.json']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
state_path=A8.parent/'work_status.json';state=read(state_path)
state['CAM_segmented_body_feed']=dict(
    publication=str((OUT/'publication.json').relative_to(A8.parent)),publication_sha256=sha(OUT/'publication.json'),
    verified_single_poses=2,single_pose_geometry='PASS',source_family_lift='BLOCKED',
    timing_adjustment='BLOCKED',temporary_lowering=pulse['status'],complete_attached_assembly='BLOCKED',
    next_design='Resolve pin 4 and H02 relative routing during bridge lift, then link rearward and bench stages',
    main_applied=False,manufacturing_release=False)
state['updated_utc']=report['generated_utc']
for item in state['remaining']:
    if item['id']=='harness':
        item['latest_segmented_feed_evidence']=str((OUT/'index.html').relative_to(A8.parent))
        item['latest_segmented_feed_detail']='两处四线排布独立通过；逐步抬升中的第4根与H02走向尚未闭合，完整装配和裁线图保持BLOCKED。'
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('CAM_SEGMENTED_FEED_REVIEW_PUBLISHED; two configurations PASS; complete assembly BLOCKED')
