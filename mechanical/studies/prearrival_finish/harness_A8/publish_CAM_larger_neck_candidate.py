"""Publish the verified local neck candidate without applying it to the robot."""
from pathlib import Path
import json,hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
specs=[('build','construction.json','build_CAM_larger_neck_candidate.py'),
       ('search','lower_bend/screen.json','plan_CAM_larger_neck_lower_bend.py'),
       ('storage','cleaned/storage.json','clean_CAM_larger_neck_storage.py'),
       ('check','verification.json','verify_CAM_larger_neck_candidate.py'),
       ('plot','plot.json','plot_CAM_larger_neck_candidate.py')]
inputs={};data={}
for name,rel,script in specs:
    p=OUT/rel;d=read(p);data[name]=d
    assert d['status']=='PASS' and d['script_sha256']==sha(A8/script)
    for q in [p,A8/script]:inputs[str(q.relative_to(ROOT))]=sha(q)
b,s,c,v,p=(data[k] for k in ('build','search','storage','check','plot'))
assert b['source_feed_sha256']==sha(OUT/'lower_bend/screen.json')
assert s['helper_sha256']==sha(A8/'build_CAM_larger_neck_candidate.py')
assert s['selected_radius_mm']==b['lower_bend_radius_mm']==10.
assert s['selected_lower_top_z_mm']==b['lower_bend_top_z_mm']==148.
assert b['source_main_sha256']==v['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
for path,h in b['protected_sources'].items():assert sha(ROOT/path)==h
assert c['source_candidate_sha256']==b['candidate_blend_sha256']==sha(OUT/'candidate.blend')
assert c['output_candidate_sha256']==v['source_candidate_sha256']==sha(OUT/'cleaned/candidate.blend')
assert v['storage_receipt_sha256']==sha(OUT/'cleaned/storage.json')
assert v['source_construction_sha256']==sha(OUT/'construction.json')
assert p['verification_sha256']==sha(OUT/'verification.json') and p['output_sha256']==sha(OUT/'comparison.png')
assert v['contact_dimensions_mm']==[1.,1.8,4.1] and v['clearance_requirement_mm']==.3
assert min(v['contact_gap_lower_bound_mm'],v['wire_gap_lower_bound_mm'])>.3
assert len(v['rows'])==4 and all(r['status']=='PASS' and r['spans']==410 for r in v['rows'])
assert len(v['pair_rows'])==6 and all(r['status']=='PASS' for r in v['pair_rows'])
assert all(d['status']=='PASS' for d in v['topology'].values())
assert v['source_objects']==209 and v['mating_allocations']==29 and v['fixed_wires']==14
assert c['unchanged_robot_objects']==207 and b['source_physical_objects_preserved']==214
for sources in (b['inherited_prints'],s['replacement_sources']):
    for row in sources.values():assert sha(ROOT/row['path'])==row['sha256'];inputs[row['path']]=row['sha256']
for q in ['candidate.blend','cleaned/candidate.blend','cleaned/Yaw_Base.npz','cleaned/Pitch_Yoke.npz',
          'verified_sections.json','comparison.png','lower_bend/selected_path.npz','wire_relaxation_curves.npz',
          'Yaw_Base_before.npz','Pitch_Yoke_before.npz','Yaw_Base.npz','Pitch_Yoke.npz']:
    inputs[str((OUT/q).relative_to(ROOT))]=sha(OUT/q)
staged=read(OUT.parent/'staged_feed/screen.json')
assert staged['script_sha256']==sha(A8/'screen_CAM_staged_neck_feed.py')
for q in [OUT.parent/'staged_feed/screen.json',A8/'screen_CAM_staged_neck_feed.py']:
    inputs[str(q.relative_to(ROOT))]=sha(q)
before=v['finite_journal_wall_samples']['before']['minimum']['thickness_mm']
after=v['finite_journal_wall_samples']['candidate']['minimum']['thickness_mm']
assert all(not row['missing'] and row['valid_rays']==12240 for row in v['finite_journal_wall_samples'].values())
removed={r['part']:r['removed_mm3'] for r in b['parts']}
md=f'''# 较大端子预留：颈部局部候选

**局部几何 PASS；独立候选，未应用主模型。完整线束仍为 BLOCKED。**

## 做了什么

统一采用上部研究的 1×1.8×4.1 mm 端子空间要求，保持 0.3 mm 模型间隙。
这仍是 ASSUMED 预留体，不是厂家完整压接外形。旧 R8 动作会靠近固定反力轴；
本次先把临时下弯道改为 **R10、竖直起点 Z148**。端子通过后，导线再回到
旧 R8/Z147 引导线；中央和上部几何基准保持，所有真实硬件位置与尺寸保持。

只在两件**已有未采用候选**上扩现有通道：Yaw_Base 再去除约 {removed['Yaw_Base']:.2f} mm³，
Pitch_Yoke 再去除约 {removed['Pitch_Yoke']:.2f} mm³。没有增加零件或改动主模型的打印件。

![真实网格剖面对比](comparison.png)

## 这次检查覆盖的范围

- 回读清理后的 Blender，209 个机器人源实体、29 个对插预留、14 根既有固定线均计入。
- 四个方向各 410 个有界连续区间：端子穿入、颈部尾线及 R10→R8 回位未检出相交。
- 端子间隙保守下界约 {v['contact_gap_lower_bound_mm']:.3f} mm；导线表面间隙下界约 {v['wire_gap_lower_bound_mm']:.3f} mm。
- 四方向两两检查共 6 组，端子与其他导线、导线之间的保守扫掠体互不相交。
- 两件保存网格均为单一闭合实体，无退化三角面。几何清理不放宽间隙要求；
  BVH 距离异常项用双精度全三角面距离复算，顶点偏差保持在 0.001 mm 内。
- 轴颈圆柱段 17 个截面、每面 720 条径向射线：最小壁厚样本 **{before:.3f}→{after:.3f} mm**。
  这是局部材料代价，不是全部零件最小壁厚或 PA12 承载合格结论。

## 还不能放行的部分

临时 R10 段比旧段多占约 {b['wire_length_supply_during_relaxation_mm']:.3f} mm 导线材料，必须由
松散的身体侧余线提供；**不是增加同样的最终裁线长度**。整段余线、公共 PH 胶壳、
手/工具操作以及身体插头最后接入尚未完成，不能把颈部通过写成整套能装。

中央直穿也作了比较：未装反力件时只有中心位置通过该直线路径检查。
这只是紧固孔处的空隙，没有完成随后移入旁侧槽位和安装轴芯的过程，未采用该装法。
原整头/上壳动作仍有碰撞，四枚 CAM 内六角螺钉仍待用户确认；本候选不替代这些事项。

下一步把身体端保持未插接，完整放置余线、PH 胶壳并验证分步装配。通道改动需在
完整方案可审阅后交用户确认；真实端子、打印配合与动态弯折仍需实物验证。

[局部验证](verification.json) · [构建记录](construction.json) · [网格清理](cleaned/storage.json) ·
[11组进线比较](lower_bend/screen.json) · [独立 Blender](cleaned/candidate.blend) ·
[此前完整装配失败证据](../index.html)
'''
(OUT/'README.md').write_text(md)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>颈部较大端子通道候选</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#243b42;background:#f5f7f7;max-width:1100px;margin:30px auto;padding:0 24px 50px}}section{{background:white;padding:22px;margin:20px 0;border-radius:10px}}.note{{background:#fff0d8}}img{{width:100%}}a{{color:#087488}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse;width:100%}}</style>
<h1>较大端子预留：颈部候选</h1><section class="note"><b>局部通过 · 未应用主模型 · 完整线束未完成</b><p>使用同一 1×1.8×4.1 mm 估算端子预留，保持 0.3 mm 间隙。临时弯道改为 R10、竖直起点上移1mm，端子通过后导线回到原 R8 路线。</p></section>
<section><img src="comparison.png" alt="较大端子临时R10路径和两件打印通道实际网格剖面对比"><p>红色为相对上一份未采用候选新增去除的区域；真实硬件及轴承位置不动，没有增加打印件。</p></section>
<section><h2>已经补上的检查</h2><table><tr><th>项目</th><th>证据范围</th></tr><tr><td>连续穿入与颈部导线回位</td><td>四方向，各410个有界区间</td></tr><tr><td>间隙下界</td><td>端子约{v['contact_gap_lower_bound_mm']:.3f}mm；导线约{v['wire_gap_lower_bound_mm']:.3f}mm</td></tr><tr><td>障碍物</td><td>209源实体＋29对插预留＋14根既有固定线</td></tr><tr><td>相互间隙与网格</td><td>6组两两检查通过；两件保存网格闭合、连通、无退化面</td></tr><tr><td>轴颈壁厚代价</td><td>12240条径向样本，最小值{before:.3f}→{after:.3f}mm；强度未验证</td></tr></table></section>
<section><h2>还不能当作完整装配通过</h2><p>身体余线和PH胶壳尚未完整放置，暂时多占的{b['wire_length_supply_during_relaxation_mm']:.3f}mm需要从松散尾线供给。整头/上壳顺序、扎带、端子入壳和其余跨关节线路仍需完成；这里没有释放裁线长度。</p><p>下一步检查身体端最后插接及全长余线；结构变化在完整候选可审阅后再确认。厂家压接成品外形、PA12配合、承载和寿命仍需实物。</p></section>
<p><a href="README.md">详细范围</a> · <a href="verification.json">几何验证</a> · <a href="cleaned/storage.json">保存网格</a> · <a href="lower_bend/screen.json">进线比较</a> · <a href="cleaned/candidate.blend">独立Blender</a> · <a href="publication.json">来源记录</a> · <a href="../index.html">完整装配问题</a></p></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Source-based publication of an unadopted local neck candidate, not complete harness release',
    script_sha256=sha(SCRIPT),source_main_sha256=b['source_main_sha256'],source_files=inputs,
    protected_files=b['protected_sources'],contact_dimensions_mm=[1.,1.8,4.1],contact_evidence='ASSUMED',
    local_continuous_neck='PASS',four_directions=4,intervals_per_direction=410,
    contact_gap_bound_mm=v['contact_gap_lower_bound_mm'],wire_gap_bound_mm=v['wire_gap_lower_bound_mm'],
    journal_wall_before_mm=before,journal_wall_candidate_mm=after,wall_sample_rays=12240,
    topology='PASS',image_visually_reviewed=True,source_objects=209,mating_allocations=29,fixed_wires=14,
    changed_candidate_parts=['Yaw_Base','Pitch_Yoke'],full_material_supply='NOT_TESTED',
    full_assembly_sequence='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    outputs={n:sha(OUT/n) for n in ('README.md','index.html')})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('LARGER_NECK_PUBLICATION PASS; local candidate only')
