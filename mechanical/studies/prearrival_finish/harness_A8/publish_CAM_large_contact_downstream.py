"""Publish consistent contact allocation evidence, keeping physical gaps open."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating'
OUT=BASE/'large_contact_downstream'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
protected=read(A8/'supplier_source_update/verification.json')['protected_files']
for name,digest in protected.items():assert sha(ROOT/name)==digest
sources={};records={}
specs=[
    ('original','screen.json','check_CAM_large_contact_downstream.py','refine_CAM_root_seating.py'),
    ('earlier','earlier_return/screen.json','plan_CAM_large_contact_return.py','check_CAM_large_contact_downstream.py'),
    ('turn','side_turn/screen.json','plan_CAM_large_contact_turn.py','plan_CAM_large_contact_return.py'),
    ('seat','root_continuous.json','check_CAM_large_contact_seating.py','check_CAM_root_seating_continuous.py'),
    ('first_continuous','side_turn/continuous.json','check_CAM_large_contact_forming.py','plan_CAM_large_contact_turn.py'),
    ('forming','start_delay/continuous.json','check_CAM_large_contact_start_delay.py','check_CAM_large_contact_forming.py')]
for key,relative,script,helper in specs:
    path=OUT/relative;data=read(path)
    assert data['source_main_sha256']==protected['mechanical/mori_v1_2.blend']
    assert data['script_sha256']==sha(A8/script) and data['helper_sha256']==sha(A8/helper)
    assert data['contact_dimensions_mm']==[1.,1.8,4.1]
    assert not data['main_applied'] and not data['manufacturing_release'] and data['whole_harness']=='BLOCKED'
    records[key]=data
    for p in [path,A8/script,A8/helper]:sources[str(p.relative_to(ROOT))]=sha(p)
seat=records['seat'];forming=records['forming'];original=records['original'];turn=records['turn']
assert original['status']==records['earlier']['status']==records['first_continuous']['status']=='BLOCKED'
assert seat['status']==turn['status']=='PASS'
assert seat['complete_coverage'] and not seat['unproved_intervals'] and len(seat['passed_intervals'])==256
if forming['status']=='PASS':
    assert forming['complete_coverage'] and not forming['unproved_intervals'] and forming['error'] is None
    assert all(r['complete'] for r in forming['coverage'])
    assert len(forming['boundary_rows'])==8 and all(r['status']=='PASS' for r in forming['boundary_rows'])
assert forming['source_failed_continuous_sha256']==sha(OUT/'side_turn/continuous.json')
assert forming['source_last_stage_candidate_sha256']==sha(OUT/'side_turn/screen.json')
assert records['first_continuous']['source_candidate_sha256']==sha(OUT/'side_turn/screen.json')
assert turn['source_original_downstream_sha256']==sha(OUT/'screen.json')
assert original['failure_poses_sha256']==sha(OUT/'failure_poses.npz')
sources[str((OUT/'failure_poses.npz').relative_to(ROOT))]=sha(OUT/'failure_poses.npz')
upstream={}
for key,relative in [('feed','ordered_feed_continuous/screen.json'),('recovery','ordered_feed_recovery/continuous.json')]:
    path=BASE/relative;d=read(path);assert d['status']=='PASS' and not d['unproved_intervals']
    upstream[key]=len(d['passed_intervals']);sources[str(path.relative_to(ROOT))]=sha(path)
count=len(forming['passed_intervals'])
forming_text=(f'四个阶段通过 {count} 个连续区间，8 个步骤边界一致。' if forming['status']=='PASS'
              else f'连续检查尚未通过；已通过 {count} 个局部区间，不能当作完整动作通过。')
open_text=('身体侧全长供线、扎带穿绕和收紧、真实端子入壳、另外七根跨关节线和 FPC、供应商最终裁线图仍未完成。'
           if forming['status']=='PASS' else '较大端子的弯线连续动作仍未完成；身体侧供线、扎带、真实端子入壳、其他线和 FPC、最终裁线图也未完成。')
table='\n'.join(f"| {r['stage']+1} | {forming['stages'][r['stage']]['active_slot']} | {r['intervals']} | {'PASS' if r['complete'] else 'BLOCKED'} |" for r in forming['coverage'])
md=f'''# CAM 端子预留尺寸统一复核

这次将上部穿线、回位、入座和弯线统一使用 **1 × 1.8 × 4.1 mm** 端子预留盒。
它是 **ASSUMED 空间分配**，不是 JST 给出的压接后最大外形。导线外径保持 0.6604 mm，
普通线间及结构间目标余量保持 0.3 mm；裸端子与导线、端子之间只检查不穿透，
允许零体积相切，不代表有制造间隙。

## 当前结果

- 上部逐根穿入：{upstream['feed']} 个连续区间通过。
- 穿出后回位：{upstream['recovery']} 个连续区间通过。
- 四根线一起入座：256 个连续区间通过；线几何保持一致，所有增大的端子重新检查。
- 后续四段弯线：{forming_text}

| 弯线阶段 | 几何槽位（非针脚号） | 连续区间数 | 完整覆盖 |
|---|---:|---:|---|
{table}

## 调整的是装配动作

较大预留盒复核时，原最后一根线的动作在俯仰舵机附近只留下约 0.273 mm 间隙，
未达到 0.3 mm 目标。单纯提前降低临时抬高量的五种尝试又使导线靠近邻线，均未采用。
组合调整临时侧转与抬高幅度后，最后一段通过 276 个有限位置检查。

随后连续检查发现第三根线一开始侧转时，预留盒与尚未弯线的相邻预留盒发生小体积重叠。
新候选先让端子分开，再侧转。{forming_text}

改动仅在独立装配研究中：没有修改打印件、孔位、舵机、导线终点或主模型。
旧小预留盒的通过记录保留其原来范围；不能用于证明较大预留盒通过。

## 检查依据

四段动作采用相同材料参数和恒定线长公式。未变的线运动仅在控制参数逐段完全一致时
引用既有连续证明；改变的两段重新检查线对结构、其他线和自身远端的间隙。
全部较大端子运动重新计算位移界限。侧转角全段为零时，端子固定的 X 区间互不穿入，
用这一解析条件处理相切；其余情况仍用位移扩大后的距离检查。

[入座连续记录](root_continuous.json) · [弯线最终连续记录](start_delay/continuous.json) ·
[原路线较大端子诊断](screen.json) · [提前回位的五种尝试](earlier_return/screen.json) ·
[微调侧转的有限候选](side_turn/screen.json) · [首次连续检查发现的起步重叠](side_turn/continuous.json)

## 仍未完成

{open_text}
身体侧当前每根约 140–162 mm 原有材料需要暂存，这不是额外裁线长度。
[身体供线材料账](../body_supply/README.md)。四枚 CAM 内六角螺钉候选仍待确认。

主模型 M1.47 保持不变。没有供应商联系、采购或制造放行。
[上部穿线和回位图](../ordered_feed_recovery/index.html) · [来源校验](publication.json)
'''
(OUT/'README.md').write_text(md)
rows=''.join(f"<tr><td>{r['stage']+1}</td><td>{forming['stages'][r['stage']]['active_slot']}</td><td>{r['intervals']}</td><td>{'PASS' if r['complete'] else 'BLOCKED'}</td></tr>" for r in forming['coverage'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 端子尺寸统一复核</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1000px;margin:30px auto;padding:0 22px 50px;background:#f4f7f6;color:#223d3e}}a{{color:#006574}}section{{background:white;padding:22px;margin:22px 0;border-radius:12px}}.note{{background:#fff0dc}}table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #ccd8d5}}</style>
<p><a href="../ordered_feed_recovery/index.html">← 上部穿线与回位</a></p><h1>统一端子预留尺寸，复核后续装配动作</h1>
<section class="note"><p>使用 1 × 1.8 × 4.1 mm 假设预留盒，未将其标作厂家完整尺寸。主模型未改，完整线束和供应商裁线图尚未放行。</p></section>
<section><h2>当前结果</h2><p>上部穿入 {upstream['feed']} 个连续区间、回位 {upstream['recovery']} 个连续区间、入座 256 个连续区间通过。弯线：{forming_text}</p>
<table><tr><th>阶段</th><th>几何槽位</th><th>连续区间</th><th>完整覆盖</th></tr>{rows}</table></section>
<section><h2>临时装配动作的两处调整</h2><p>第三根线先让端子拉开距离，再侧转；最后一根轻微调整临时抬高与侧转。打印结构和最终导线形状保持不变。</p><p>原较大预留盒路线在舵机旁只余约 0.273 mm；仅提前降低高度会靠近邻线。随后连续检查又检出起步侧转的预留盒重叠，分别保留了诊断记录。</p></section>
<section><h2>完整工序仍缺的部分</h2><p>{open_text}</p><p><a href="../body_supply/README.md">身体侧约 140–162 mm 原有材料暂存</a>尚未建模；它不是增加裁线长度。实际端子和压接外形仍待厂家资料或首件核对。</p></section>
<p><a href="README.md">完整说明</a> · <a href="root_continuous.json">入座连续记录</a> · <a href="start_delay/continuous.json">弯线连续记录</a> · <a href="side_turn/continuous.json">原起步重叠诊断</a> · <a href="screen.json">原舵机间隙诊断</a> · <a href="publication.json">来源校验</a></p></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Source-consistent publication only; whole harness remains unclosed',
    script_sha256=sha(SCRIPT),generated_utc=datetime.now(timezone.utc).isoformat(),protected_files=protected,
    source_files=sources,contact_dimensions_mm=[1.,1.8,4.1],root_seating_continuous='PASS',root_seating_intervals=256,
    forming_continuous=forming['status'],forming_intervals=count,forming_complete=forming['complete_coverage'],
    body_supply='BLOCKED',whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    outputs={name:sha(OUT/name) for name in ['README.md','index.html']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for name,digest in protected.items():assert sha(ROOT/name)==digest
print('CAM_LARGE_CONTACT_PUBLICATION PASS; forming',forming['status'],count,'whole harness BLOCKED',flush=True)
