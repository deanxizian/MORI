"""Publish the ordered CAM feed milestone without releasing the harness."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating'
OUT=BASE/'ordered_feed_recovery'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=read(A8/'supplier_source_update/verification.json')['protected_files']
for name,digest in protected.items():assert sha(ROOT/name)==digest
feed=read(BASE/'shifted_ordered_feed_handle05/screen.json')
recovery=read(OUT/'screen.json');retract=read(BASE/'ordered_feed_retraction/screen.json')
render=read(OUT/'render_manifest.json');sources={}
feed_cont=read(BASE/'ordered_feed_continuous/screen.json')
feed_audit=read(BASE/'ordered_feed_continuous/bound_audit.json')
recovery_cont=read(OUT/'continuous.json');recovery_math=read(OUT/'math_bounds.json')
body_audit=read(BASE/'body_supply/audit.json')
large_path=BASE/'large_contact_downstream/publication.json';large=read(large_path)
assert large['status']==large['root_seating_continuous']==large['forming_continuous']=='PASS'
assert large['forming_complete'] and large['root_seating_intervals']==256 and large['forming_intervals']==1735
assert large['contact_dimensions_mm']==[1.,1.8,4.1] and not large['main_applied']
assert large['script_sha256']==sha(A8/'publish_CAM_large_contact_downstream.py')
for name,digest in large['source_files'].items():assert sha(ROOT/name)==digest
for name,digest in large['outputs'].items():assert sha(large_path.parent/name)==digest
for p in [large_path,A8/'publish_CAM_large_contact_downstream.py',large_path.parent/'README.md',large_path.parent/'index.html']:
    sources[str(p.relative_to(ROOT))]=sha(p)
for path,data,script,helper in [
    (BASE/'shifted_ordered_feed_handle05/screen.json',feed,'plan_CAM_shifted_upper_feed.py','plan_CAM_ordered_upper_feed.py'),
    (OUT/'screen.json',recovery,'plan_CAM_ordered_feed_recovery.py','plan_CAM_shifted_upper_feed.py'),
    (BASE/'ordered_feed_retraction/screen.json',retract,'check_CAM_ordered_feed_retraction.py','plan_CAM_shifted_upper_feed.py'),
    (OUT/'render_manifest.json',render,'render_CAM_ordered_feed_recovery.py','render_CAM_contact_refined_forming.py')]:
    assert data['status']=='PASS' and data['source_main_sha256']==protected['mechanical/mori_v1_2.blend']
    assert data['script_sha256']==sha(A8/script) and data['helper_sha256']==sha(A8/helper)
    assert not data['main_applied'] and not data['manufacturing_release'] and data['whole_harness']=='BLOCKED'
    for p in [path,A8/script,A8/helper]:sources[str(p.relative_to(ROOT))]=sha(p)
selected=next(r for r in feed['rows'] if r['allocation']=='requested_space_only' and r['status']=='PASS')
assert len(selected['stages'])==4 and all(s['status']=='PASS' for s in selected['stages'])
count=sum(s['checked_positions'] for s in selected['stages']);assert count==4205
assert len(recovery['rows'])==41 and all(r['result']['status']=='PASS' for r in recovery['rows'])
assert recovery['boundary_match']=='PASS' and recovery['maximum_boundary_difference_mm']<.0001
assert recovery['minimum_radius_lower_mm']>=7.
assert len(retract['rows'])==4 and all(r['status']=='PASS' for r in retract['rows'])
assert recovery['source_feed_sha256']==retract['source_feed_sha256']==sha(BASE/'shifted_ordered_feed_handle05/screen.json')
assert render['source_screen_sha256']==sha(OUT/'screen.json')
for p,digest in [(BASE/'shifted_ordered_feed_handle05/curves.npz',feed['curves_sha256']),
                 (OUT/'curves.npz',recovery['curves_sha256']),
                 (OUT/'review.blend',render['review_sha256'])]:
    assert sha(p)==digest;sources[str(p.relative_to(ROOT))]=digest
for im in render['images']:
    p=OUT/im['file'];assert sha(p)==im['sha256'];sources[str(p.relative_to(ROOT))]=im['sha256']
for path,data,script,helper in [
    (BASE/'ordered_feed_continuous/screen.json',feed_cont,'check_CAM_ordered_feed_continuous.py','plan_CAM_shifted_upper_feed.py'),
    (BASE/'ordered_feed_continuous/bound_audit.json',feed_audit,'audit_CAM_ordered_feed_bounds.py','check_CAM_ordered_feed_continuous.py'),
    (OUT/'continuous.json',recovery_cont,'check_CAM_ordered_recovery_continuous.py','plan_CAM_ordered_feed_recovery.py')]:
    assert data['status']=='PASS' and data['source_main_sha256']==protected['mechanical/mori_v1_2.blend']
    assert data['script_sha256']==sha(A8/script) and data['helper_sha256']==sha(A8/helper)
    assert not data['main_applied'] and not data['manufacturing_release']
    for p in [path,A8/script,A8/helper]:sources[str(p.relative_to(ROOT))]=sha(p)
assert len(feed_cont['passed_intervals'])==1228 and not feed_cont['unproved_intervals']
assert all(r['complete'] for r in feed_cont['coverage'])
assert recovery_cont['complete_coverage'] and len(recovery_cont['passed_intervals'])==256 and not recovery_cont['unproved_intervals']
assert recovery_cont['source_math_sha256']==sha(OUT/'math_bounds.json')
assert feed_audit['source_continuous_sha256']==sha(BASE/'ordered_feed_continuous/screen.json')
assert recovery_math['status']=='PASS' and recovery_math['script_sha256']==sha(A8/'audit_CAM_ordered_recovery_math.py')
assert body_audit['audit_status']=='PASS' and body_audit['status']=='BLOCKED'
assert body_audit['script_sha256']==sha(A8/'audit_CAM_body_supply.py')
for p in [OUT/'math_bounds.json',A8/'audit_CAM_ordered_recovery_math.py',
          BASE/'ordered_feed_continuous/BOUND_METHOD.md',BASE/'body_supply/audit.json',
          BASE/'body_supply/README.md',A8/'audit_CAM_body_supply.py']:
    sources[str(p.relative_to(ROOT))]=sha(p)
md=f'''# CAM 逐根穿线与回位候选

主模型 M1.47 保持不变。这里使用尚未采用的 J3M/CAM 固定座研究几何，展示装配顺序；不是供应商制作图或完整装配放行。

## 当前结果

四根线按几何槽位 **3 → 2 → 1 → 0** 穿入。这个编号不是电气针脚号。

1. 未穿的线先留在颈部出口上方 13 mm。轮到该线时，沿原竖直方向退回，再进入弯曲路线；四组整段端子扫掠及初始微小转向的包络检查通过。**这仍要求下方能送线/退线，相关整段余线尚未设计。**
2. 每次只穿一根，先穿好的线完整保留，其余线也留在检查中。上端暂不向 CAM 固定位置收拢。所选较大空间分配通过 {count} 个有限位置检查；新增 **1228 个连续区间**覆盖完整上部行程。另有 11016 次端子角点位姿对照和 84 次竖直位姿对照，用于核对运动界限实现。
3. 四根全部穿入后，临时 X 偏移 0.2 mm、Y 偏移 1.8 mm 逐渐回到既有入座起点，并恢复上方 X 过渡。41 个有限位置及新增 **256 个连续区间**通过；全程半径、自由末端长度和普通线间间隙分别用独立数学界限检查。
4. 回位终点与既有侧向入座起点的最大坐标差约 {recovery['maximum_boundary_difference_mm']:.8f} mm，小于明示的 0.0001 mm 数值衔接限值。同样较大端子预留盒已通过后续入座的 256 个连续区间，以及调整临时装配动作后的四段弯线 1735 个连续区间。[后续尺寸统一复核](../large_contact_downstream/index.html)。

弯曲段采用解析圆弧或有界 Bezier/五次曲线。41 个回位位置的最小半径下界 {recovery['minimum_radius_lower_mm']:.4f} mm，当前设计要求 7 mm；末端直线至少保留 {recovery['minimum_terminal_straight_mm']:.4f} mm。长度差只由自由末端直线补偿，不拉长导线。总长基于既有折线分配，不是最终裁线长度。

## 空间与资料边界

- 导线外径 0.6604 mm；普通结构和线间采用 0.3 mm 名义表面余量。
- 这里的端子 **1 × 1.8 × 4.1 mm** 是请求的空间分配，**ASSUMED**，不是 JST 给出的完整最大外形。端子对导线和其他端子只检查不穿透，没有宣称 0.3 mm 端子间余量。
- 旧 0.8 × 1.35 × 3.9 mm 方盒在另一条临时路线下也通过有限位置检查，不能把两个方案当作完全相同的动作。
- [JST 官方 SH 图纸](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)与[APSH 目录](https://www.jst-mfg.com/product/pdf/eng/eAPSH.pdf)可用于核对同料号 SSH-003T-P0.2-H。锁止弹片及完成压接后的完整外形没有由本研究确认。
- 根部扎带在这几步尚未安装。其穿绕、收紧，以及实际端子入壳仍未完成。

## 查看

![全部穿出后，暂时保持上端竖直](after_feed.png)

![恢复上方过渡后，准备侧向入座](ready_to_seat.png)

![根部位置细节](root_detail.png)

[独立 Blender 研究文件](review.blend) · [41 个回位位置及长度/曲率记录](screen.json) · [逐根穿入检查](../shifted_ordered_feed_handle05/screen.json) · [回退衔接扫掠](../ordered_feed_retraction/screen.json)

## 下方供线审查

现有上部过程还没有放置身体侧剩余材料：从 13 mm 暂存位置开始，每根约有 140–149 mm 未纳入模型；退回穿线起点后，每根约 153–162 mm。它们是原有材料的暂存需求，不是额外增加裁线长度。[材料账与下一步装配研究](../body_supply/README.md)。

拟评估先在机身外完成头部穿线，身体端保持松散，再让完整头部总成带线落位。旧身体装配报告只含桥和轴承，不能直接当作完整带线头部的验证。

[上部连续检查](../ordered_feed_continuous/screen.json) · [运动界限与角点核对](../ordered_feed_continuous/BOUND_METHOD.md) · [回位连续检查](continuous.json) · [全程曲率与长度界限](math_bounds.json)

完整线束仍 BLOCKED：下方供线、扎带、实际端子插装、其他七根跨关节线和 FPC、供应商最终裁线图尚未全部完成。没有修改硬件文件、提交供应商表单或下单。
'''
(OUT/'README.md').write_text(md)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM 逐根穿线候选</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1060px;margin:30px auto;padding:0 22px 60px;color:#223d3e;background:#f4f7f6}}a{{color:#006574}}section{{background:white;padding:22px;margin:22px 0;border-radius:12px}}.note{{background:#fff0dc}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}img{{width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd8d5}}table{{width:100%;border-collapse:collapse}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style>
<p><a href="../../../../../supplier_source_update/index.html">← 供应商资料与设计进度</a></p><h1>CAM 四线逐根穿入，再回到固定位置</h1>
<section class="note"><p>独立装配候选，主模型 M1.47 未改。上部穿入、回位、入座与四段弯线已按同样较大端子预留尺寸通过连续名义几何检查；身体侧完整供线、扎带和真实端子入壳仍未完成，制造图未放行。</p></section>
<section><h2>现在接通了哪些步骤</h2><table><tr><th>步骤</th><th>结果与限制</th></tr>
<tr><td>从暂存位置退回，再转入弯曲路线</td><td>4 组整段端子扫掠与微小初始转向通过；需要下方余线能退让</td></tr>
<tr><td>按槽位 3 → 2 → 1 → 0 逐根穿入</td><td>{count} 个有限位置及 1228 个连续区间通过，其他导线保留；编号不是电气针脚号</td></tr>
<tr><td>全部穿出后回位</td><td>41 个位置及 256 个连续区间通过；另有全程曲率、长度与平行线间距界限</td></tr>
<tr><td>接到入座与弯线动作</td><td>名义坐标衔接通过；同样较大预留盒的入座 256 个连续区间、弯线 1735 个连续区间通过。<a href="../large_contact_downstream/index.html">查看后续复核</a></td></tr></table></section>
<section><h2>回位前后</h2><div class="grid"><figure><img src="after_feed.png" alt="四根完整导线穿入后，上方保持竖直"><figcaption>1. 全部穿出，上端暂不收拢</figcaption></figure><figure><img src="ready_to_seat.png" alt="上方过渡恢复后准备侧向入座"><figcaption>2. 恢复上方过渡，准备侧向入座</figcaption></figure></div><img src="root_detail.png" alt="四根导线经过头部舵机附近的局部视图"></section>
<section><h2>尺寸证据与还没完成的内容</h2><p>导线外径 0.6604 mm。金色端子为 1 × 1.8 × 4.1 mm 请求空间，ASSUMED，不是厂家完整最大尺寸。普通结构及线间留 0.3 mm；端子之间仅检查不穿透。</p><p>末端直线至少保留 {recovery['minimum_terminal_straight_mm']:.3f} mm，长度差由自由直线补偿。当前分配不是供应商裁线尺寸。真实端子、下方供线、扎带及其余跨关节线路/FPC 仍需完成。</p><p><a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH 官方图纸</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/eAPSH.pdf">同料号 APSH 细节图</a></p></section>
<section><h2>下一步：补全身体侧供线</h2><p>当前上部检查没有放置身体侧尚未送入的材料，每根约需处理 140–162 mm 的暂存段，随工序变化。它不是给最终线束额外加长。</p><p>接下来评估头部在机身外先穿线，身体端保持松散，再核对完整带线总成落位与身体侧理线。旧桥/轴承装配检查不能直接代替。</p><p><a href="../body_supply/README.md">材料账与装配依赖</a></p></section>
<p><a href="review.blend">独立 Blender 文件</a> · <a href="README.md">完整说明</a> · <a href="../ordered_feed_continuous/screen.json">上部连续穿入</a> · <a href="../ordered_feed_continuous/BOUND_METHOD.md">运动界限推导</a> · <a href="continuous.json">连续回位</a> · <a href="math_bounds.json">全程曲率与长度</a> · <a href="../ordered_feed_retraction/screen.json">回退衔接</a> · <a href="publication.json">来源校验</a></p></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Publication and bounded source receipt, not complete assembly or manufacturing approval',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    protected_files=protected,source_files=sources,feed_finite_positions=count,recovery_finite_positions=41,
    retraction_sweeps=4,feed_continuous='PASS',recovery_continuous='PASS',
    feed_continuous_intervals=1228,recovery_continuous_intervals=256,
    larger_contact_seating='PASS',larger_contact_seating_intervals=256,
    larger_contact_forming='PASS',larger_contact_forming_intervals=1735,
    larger_contact_publication_sha256=sha(large_path),
    body_supply='BLOCKED',body_supply_audit='PASS',
    boundary_match='PASS',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    outputs={n:sha(OUT/n) for n in ['README.md','index.html']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_ORDERED_FEED_PUBLICATION PASS; complete harness BLOCKED')
