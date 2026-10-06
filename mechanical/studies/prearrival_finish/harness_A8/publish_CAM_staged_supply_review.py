"""Publish source-preserving staged assembly and complete-stock diagnostics."""
from pathlib import Path
import hashlib,html,json,sys
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
FULL=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head'
OUT=FULL/'split_assembly';STOCK=FULL/'bridge_wire_stock'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
specs=[
 ('split',OUT/'screen.json','screen_CAM_split_head_assembly.py'),
 ('pitch',OUT/'pitch_stages/screen.json','screen_CAM_staged_pitch_installation.py'),
 ('contacts',OUT/'pitch_stages/interface_contacts/diagnosis.json','diagnose_CAM_staged_interface_contacts.py'),
 ('stock',STOCK/'screen.json','screen_CAM_bridge_wire_stock.py'),
 ('flex',STOCK/'body_fixed_flex/screen.json','plan_CAM_bridge_stock_flex.py'),
 ('PH',STOCK/'PH_open_bridge/screen.json','plan_CAM_PH_open_bridge_entry.py'),
 ('slide',STOCK/'bridge_over_stock/screen.json','screen_CAM_bridge_over_stock.py'),
 ('sections',OUT/'review/sections.json','extract_CAM_staged_supply_sections.py'),
 ('plots',OUT/'review/plots.json','plot_CAM_staged_supply_review.py'),
]
inputs={};data={};source_hash=sha(ROOT/'mechanical/mori_v1_2.blend')
for label,path,script in specs:
    d=read(path);data[label]=d
    assert d['script_sha256']==sha(A8/script),script
    assert d['source_main_sha256']==source_hash,label
    assert not d['main_applied'],label
    for p in [path,A8/script]:inputs[str(p.relative_to(ROOT))]=sha(p)
    for p,digest in d.get('source_files',{}).items():
        assert sha(ROOT/p)==digest,p;inputs[p]=digest
    for p,digest in d.get('protected_sources',{}).items():assert sha(ROOT/p)==digest,p
    for p,row in d.get('substituted_unadopted_prints',{}).items():
        assert sha(ROOT/row['path'])==row['sha256'],p;inputs[row['path']]=row['sha256']
split,pitch,contacts,stock,flex,ph,slide,sections,plots=(data[k] for k in ['split','pitch','contacts','stock','flex','PH','slide','sections','plots'])
assert sum(len(v) for v in split['membership'].values())==209
assert len(set.union(*(set(v) for v in split['membership'].values())))==209
assert len(pitch['yaw_members'])==21 and len(pitch['pitch_membership']['cradle_CAM'])==14
assert all(r['status']=='PASS' for r in split['rows'][:4])
assert sum(r['checked_positions'] for r in split['rows'][:4])==408
assert [r['checked_positions'] for r in contacts['order_rows']]==[181,141]
assert all(r['status']=='PASS' for r in contacts['order_rows'])
assert len(contacts['order_rows'][0]['moving'][0])==22
assert all(d['whole_harness']=='BLOCKED' for d in [split,pitch,contacts,stock,flex,ph,slide])
assert stock['status']==flex['status']==ph['status']==slide['status']=='BLOCKED'
assert ph['rows'][0]['status']=='PASS' and ph['rows'][1]['stop']=='bounded_grid_exhausted'
assert len(flex['rows'])==10 and all(r['status']=='BLOCKED' for r in flex['rows'])
assert stock['rows'][-1]['status']==slide['rows'][-1]['status']=='PASS'
assert all(d['present_source_objects']==122 and d['source_objects']==209 and d['fixed_wire_solids']==14 and d['mating_allocations']==29 for d in [stock,flex,ph,slide])
source_contacts={(r['a'],r['b']):r for r in contacts['source_contacts']}
frame=source_contacts[('Head_Front','Display_Frame')]
lcd=source_contacts[('Head_Front','Display_PCB')]
assert .007<frame['intersection_mm3']<.008 and lcd['intersection_mm3']<1e-9
refresh=next(r for r in split['validation_proxy_pose_refresh'] if r['part']=='Display_PCB')
assert .14<refresh['previous_front_shell_overlap_mm3']<.16 and refresh['refreshed_front_shell_overlap_mm3']<1e-9
for r in contacts['source_contacts']:
    p=ROOT/r['overlap_mesh'];inputs[r['overlap_mesh']]=sha(p)
for p,digest in plots['source_reports'].items():assert sha(ROOT/p)==digest,p
assert plots['sections_sha256']==sha(OUT/'review/sections.json')
for p,digest in plots['outputs'].items():
    assert sha(OUT/'review'/p)==digest,p;inputs[str((OUT/'review'/p).relative_to(ROOT))]=digest
assert '--visual-reviewed' in sys.argv,'Review the three generated figures before publishing.'
length_rows=''.join(f"<tr><td>{r['geometric_slot']}</td><td>{r['full_nominal_allocation_mm']:.2f}</td><td>{r['upright_stock_mm']:.2f}</td></tr>" for r in stock['lengths'])
data_links=''.join(f'<li><a href="{path.relative_to(OUT) if path.is_relative_to(OUT) else "../"+str(path.relative_to(FULL))}">{html.escape(label)}：原始结果</a></li>' for label,path,_ in specs)
md=f'''# 分步装配与完整 CAM 线长：本轮补查

**局部装配顺序有进展，完整线束仍为 BLOCKED。主模型 M1.47、结构参数和硬件文件未改。**

## 更合理的刚体顺序

身体上壳与固定承重桥先落位（408 个有限位置），再从上方装偏航组件及舵盘
（22 件，181 个位置），接着放头托与 CAM（14 件，141 个位置），最后装两侧短轴。
这些有限位置未检出名义刚体相交；原动画中把舵盘随头托一起下降的组合会碰到输出件。
尚未更新主动画，因为完整线束与反力夹初装仍未完成。SCS0009 舵盘、短轴与锁紧仍待厂家依据。

![分步装配](review/assembly_order.png)

## 四根线的完整材料已经放进候选

本轮把每根既有名义全长都保留，约 153–162 mm 的头侧未装材料暂时竖直放在头部上方。
身体共同 PH 胶壳、28 个其他插接分配体及 14 根既有电源/信号线也纳入检查。
这是新的完整材料候选，不是裁线尺寸，也没有把临时余线额外加到最终线长。

![完整线长](review/wire_stock.png)

| 动作候选 | 已证实的结果 |
| --- | --- |
| 插头与整条线随承重桥移动 | 首次抬升间隙下界不足；后移/抬高阶段胶壳与既有导线发生名义相交 |
| 身体端插头不动，前段导线变形 | 10 组有限变形候选都遇到间隙或弯曲半径筛查问题 |
| 承重桥沿固定竖直线尾滑动 | 下方弯道与承重桥/轴承的间隙要求未满足 |
| PH 胶壳由开口颈部穿入 | 直线退出 8 mm 的分配体检查通过；固定姿态、2 mm 网格搜索未找到通路 |
| 桥已落位，身体上壳最后归位 | 两种全线长候选各 61 个有限位置未检出碰撞；不能替代前面未通过的步骤 |

检查没有隐藏固定导线、缩小插头或端子，也没有降低 0.3 mm 项目间隙分配。
有些失败是保守间隙界限不足，并不等于实际穿透。所试路线有限，不代表所有方案都不可能。
下一步需要把身体段和颈部段的临时形状一同设计；没有理由因此再改变供应商制作方式。

## 修正检查误报，保留真实待处理项

隐藏的 LCD 碰撞代理未同步到当前姿态，曾造成约 0.148 mm³ 相交误报。
统一依赖图求值后，该处名义相交为 0，不改 LCD 或头壳。
相机支架上角与前壳的 **{frame['intersection_mm3']:.8f} mm³** 小相交仍存在，需处理局部间隙并核对壳厚和装入路径。
Pitch 锁紧件约 0.000036 mm³ 的源接口接触也单独记录；未把未定型舵盘接口当作合格配合。

![局部剖面与代理修正](review/contact_sections.png)

已统一重算相关新检查。全部结果只是名义几何诊断；真实线材/压接外形、夹持、扎带、工具、
其余跨关节线与 FPC、连续路径及 PA12 强度仍未闭合。候选打印件尚未采用，无制造放行。

[结果与来源](publication.json) · [刚体分组](screen.json) · [头部后装顺序](pitch_stages/screen.json) ·
[源接口诊断](pitch_stages/interface_contacts/diagnosis.json) · [完整供线原始结果](../bridge_wire_stock/screen.json) ·
[上一级汇总](../index.html)
'''
(OUT/'README.md').write_text(md)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 分步装配与完整线长</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#213b43;background:#f6f8f8;max-width:1020px;margin:32px auto;padding:0 24px 50px}}section{{background:#fff;padding:24px;margin:22px 0;border-radius:10px}}.note{{background:#fff0d8}}img{{max-width:100%;height:auto}}.wire{{max-width:680px}}a{{color:#087e83}}td,th{{padding:9px 16px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse}}</style>
<a href="../index.html">← 全段装配补查</a><h1>分步装配有进展，完整供线仍需处理</h1>
<section class="note"><b>本轮完成了更完整的诊断，没有修改主模型。</b><p>把舵盘提前随偏航组件装入、两侧短轴后装，名义刚体顺序可以继续。四根 CAM 线的全长与共同 PH 插头已建入候选，几个身体阶段仍有间隙或相交问题。供应商按图制作已确定；路线和裁线图仍由项目完成。</p></section>
<section><h2>先后顺序</h2><img src="review/assembly_order.png" alt="偏航与舵盘先装、头托后装、短轴最后装的候选顺序"><p>209 个机器人源实体全部归组，后装件有逐项清单。前四段身体/承重桥动作共检查 408 个有限位置；22 件偏航总成检查 181 个位置；14 件头托总成检查 141 个位置。只是所查刚体动作通过，尚不包含完整线束、握持及全部工具动作。主动画暂未改，舵盘/短轴仍待厂家接口资料。</p></section>
<section><h2>完整线长已建入，临时存放还没有可行全流程</h2><img class="wire" src="review/wire_stock.png" alt="保留四根名义全长，在头部上方临时存放线尾的侧视投影"><table><tr><th>几何槽位</th><th>名义路线总长 / mm</th><th>上方直线余量 / mm</th></tr>{length_rows}</table><p>这是中心线模型账，不是供应商裁线长度；未确认压接端部补偿。PH 胶壳、28 个其他插接包络、14 根既有固定导线均保留。</p><ul><li>插头随桥移动：后移阶段与 H01 线相交约 1.76 mm³，较高位置与 H04 线相交约 5.10 mm³。</li><li>插头固定、导线变形：10 组限定曲线未通过间隙或半径筛查。</li><li>承重桥沿固定线尾滑动：下方弯道在既有抬升动作中间隙不足。</li><li>插头从颈部穿入：轴向退出 8 mm 的分配体检查通过；固定姿态的 2 mm 网格搜索穷尽其连通区域，未找到到颈部的通路。没有排除转动插头等其他动作。</li><li>桥已落位后，上壳归位的 61 个位置在两种全长候选中通过；前面的供线动作仍需解决。</li></ul><p>间隙下界未满足不等于已发生实体穿透；所有结论限定于各自受检方案。</p></section>
<section id="source-contact"><h2>修正 LCD 误报，保留相机支架问题</h2><img src="review/contact_sections.png" alt="相机支架上角与前壳的真实模型相交剖面，以及修正隐藏LCD代理姿态后的结果"><p>LCD 碰撞代理曾因隐藏而未刷新父级变换。统一求值后，该处名义相交为零，不改真实部件。相机支架上角仍与前壳相交约 {frame['intersection_mm3']:.5f} mm³，需要处理局部间隙、壳厚和装入路径。Pitch 锁紧件的小接触另列在厂家接口项；没有放行未知配合。</p></section>
<section><h2>下一步</h2><p>一起规划身体段与颈部段的临时线形；完成相机支架局部间隙候选，再把扎带、端子入壳、握持工具及其余线/FPC纳入装配检查。结构变化仍先提供具体候选审阅。没有发供应商消息或下单。</p><p>主模型、参数、机械合同和硬件合同哈希均保持。强度、实际压接和实物配合未验证。</p></section>
<details><summary>来源与检查数据</summary><ul>{data_links}</ul><p><a href="README.md">完整说明</a> · <a href="publication.json">发布记录</a></p></details></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Published corrected nominal diagnostics; complete wire supply and assembly remain unfinished',
 script_sha256=sha(SCRIPT),source_main_sha256=source_hash,protected_files=split['protected_sources'],source_files=inputs,
 source_objects=209,assigned_source_objects=209,body_rigid_positions=408,yaw_with_horn_members=22,yaw_with_horn_positions=181,
 cradle_CAM_members=14,cradle_CAM_positions=141,complete_four_wire_material_present=True,
 complete_four_wire_material_scope='Four full nominal polylines in each stated temporary family, not a proven complete procedure or cut lengths',
 nominal_wire_lengths_mm=[r['full_nominal_allocation_mm'] for r in stock['lengths']],
 temporary_upright_lengths_mm=[r['upright_stock_mm'] for r in stock['lengths']],
 full_material_supply='BLOCKED',fixed_housing_families=10,PH_grid_expanded=ph['rows'][1]['expanded_nodes'],
 PH_search_scope='Fixed orientation, 2mm bounded grid; does not exclude rotation or other staging',
 source_proxy_pose_refresh=split['validation_proxy_pose_refresh'],LCD_overlap_after_refresh_mm3=lcd['intersection_mm3'],
 front_camera_support_overlap_mm3=frame['intersection_mm3'],front_camera_support_clearance='BLOCKED',
 whole_harness='BLOCKED',continuous_full_assembly='NOT_TESTED',transmission_interfaces='BLOCKED',
 images_visually_reviewed=True,main_applied=False,manufacturing_release=False,
 outputs={n:sha(OUT/n) for n in ['README.md','index.html']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('STAGED_SUPPLY_PUBLICATION PASS; full supply BLOCKED; main unchanged')
