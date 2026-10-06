"""Publish the verified staged order without claiming full attached-wire assembly."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,sys
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;P=A8.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'review';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert '--visual-reviewed' in sys.argv,'Inspect both generated images before publishing'
dense=read(BASE/'dense.json');trial=next(r for r in dense['trials'] if r['label']=='defer_H01_H02_H04')
assert dense['status']==trial['status']=='PASS' and sum(r['checked_positions'] for r in trial['rows'])==408
paths=read(BASE/'later_connections/grid_margin_approach/screen.json')
verified=read(BASE/'later_connections/grid_margin_approach/verification.json')
projections=read(OUT/'projections.json');plots=read(OUT/'plots.json')
h02dir=BASE/'H02_preinstalled';h02=read(h02dir/'publication.json')
assert h02['status']=='PASS' and h02['H02_preinstalled_candidate']=='PASS'
assert h02['script_sha256']==sha(A8/'publish_H02_preinstalled_route.py')
for p,h in h02['source_files'].items():assert sha(ROOT/p)==h,p
for p,h in h02['outputs'].items():assert sha(h02dir/p)==h,p
assert len(paths['rows'])==6 and all(r['status']=='PASS' for r in paths['rows'])
assert all(r['full_0_3_margin_status']=='PASS' for r in verified['rows'])
assert verified['paths_sha256']==projections['paths_sha256']==sha(BASE/'later_connections/grid_margin_approach/screen.json')
assert verified['script_sha256']==sha(A8/'verify_CAM_later_ports_paths.py')
assert paths['optimizer_base_sha256']==sha(A8/'plan_CAM_later_ports_grid.py')
assert paths['script_sha256']==sha(A8/'plan_CAM_later_ports_margin.py')
assert plots['script_sha256']==sha(A8/'plot_CAM_first_order_review.py')
assert plots['projections_sha256']==sha(OUT/'projections.json')
for f,d in plots['outputs'].items():assert sha(OUT/f)==d
for p,h in dense['protected_sources'].items():assert sha(ROOT/p)==h
for item in dense['substituted_unadopted_prints'].values():assert sha(ROOT/item['path'])==item['sha256']
inputs={}
inputs[str((h02dir/'publication.json').relative_to(ROOT))]=sha(h02dir/'publication.json')
inputs[str((A8/'publish_H02_preinstalled_route.py').relative_to(ROOT))]=sha(A8/'publish_H02_preinstalled_route.py')
for p in [BASE/'screen.json',BASE/'dense.json',BASE/'later_connections/screen.json',
          BASE/'later_connections/connector_approach/screen.json',
          BASE/'later_connections/grid_approach/screen.json',BASE/'later_connections/grid_approach/verification.json',
          BASE/'later_connections/grid_margin_approach/screen.json',BASE/'later_connections/grid_margin_approach/verification.json',
          OUT/'projections.json',OUT/'plots.json']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
for name in ['screen_CAM_bridge_wire_stock.py','screen_CAM_body_install_order.py','verify_CAM_body_install_order.py',
             'screen_CAM_later_body_connections.py','plan_CAM_later_connector_approach.py','plan_CAM_later_ports_grid.py',
             'plan_CAM_later_ports_margin.py','verify_CAM_later_ports_paths.py','extract_CAM_first_order_review.py','plot_CAM_first_order_review.py']:
    inputs[str((A8/name).relative_to(ROOT))]=sha(A8/name)
md='''# CAM 先装与身体线束后装：独立顺序候选

**本轮完成了身体阶段的有限位置检查，以及六个后装插头的连续接入路径。完整带线装配仍为 BLOCKED。**

## 明确先装和后装

先让四根 CAM 导线、共同 PH 插头及固定承重桥随同安装，H03 的两根导线保留。
H01、H02、H04 的 12 根导线和 6 个插头明确延后；不是把这些零件从最终装配删掉。
身体核心 94 件、上壳 22 件、承重桥 6 件均参与计算，共 122 件源部件。
偏航与俯仰总成在这一阶段尚未装入。

使用四根完整名义线长（约 287.29、327.86、285.09、339.61 mm），保留头上方临时竖直线尾。
这些是模型中的路径长度，**不是供应商裁线尺寸**。不额外截短导线以通过检查。

| 阶段 | 有限检查位置 | 本轮结果 |
|---|---:|---|
| 上壳保持 15° / 上移 14 mm，承重桥上下移动 | 37 | PASS |
| 上壳与承重桥后移 14 mm | 57 | PASS |
| 整段提起至装配台位置 | 253 | PASS |
| 桥已落座，上壳回位 | 61 | PASS |

共 408 个位置；安装采用相反次序。有限位置不等于身体过程的连续运动证明。
独立支撑和人手操作仍需检查。研究使用尚未应用的颈部 / 头托候选，不能称作主模型装配已通过。

![候选顺序](order.png)

## 六个后装插头的路径

H01：power_J17 / motion_J1；H02：motion_J2 / power_J13；H04：motion_J4 / imu_J1。
最初沿插接轴退出 8 mm 后，采用小幅绕行再从上方或侧方退出；反向即接入。
每条路径检查时，**其他插头保留最终位置**，完整四根 CAM 线与 H03 导线也保留。

六条路径均通过保存结果复核。自由移动段用整个凸体扫掠加 ±0.3 mm 包络检查结构；
对 CAM 线使用包含检查、采样间距和源曲线弦误差界限，保留 0.3 mm 名义余量。
最初 8 mm 插接段只做名义外形检查，保留原有自身插座的接合体积；没有放宽后续运动的碰撞条件。
真实插头轮廓、端子插合和制造公差仍未确认。

![六个插头的接入路径](connector_paths.png)

## 仍未完成的设计

- H01、H02、H04 连线后的柔性送入过程、临时弯曲半径、线长与相互次序；本轮是插头本体检查。
- 后续偏航组件从上方装入时，如何处理当前临时竖直线尾。
- 扎带穿绕和收紧、手部与工具空间、其余跨关节线和 FPC。
- 结合最终工序确定分支、长度基准和供应商裁线图。

先前整束刚性上提的失败不代表柔性线束无法安装。新增路径也不能据此放行完整线束。
M1.47 主模型、配置和硬件合同未改；未发制造图或采购单。

[身体位置检查](../dense.json) · [六条带余量路径](../later_connections/grid_margin_approach/screen.json) · [保存路径复核](../later_connections/grid_margin_approach/verification.json)
'''
addition='''## 后续线长复核：H02 改为先装

前一轮六条是裸插头路径。接上现有名义线长后，H02 与 H04 部分位置不满足必要长度下界，不能作为整束装配方案。
H02 已有较低的独立走线候选：开敞机身内先接好 H02/H03，再装 CAM 与桥；H01/H04 继续后装。
H02 两端插头与完整线形竖直落入通过201个有限位置，随后身体408个位置与头部130个姿态复核通过。
不改打印件或接口，线长尚非供应商裁线尺寸。H01/H04 的10根导线带线装入仍未完成。
[查看新走向、线长问题和具体范围](../H02_preinstalled/index.html)。

以下图片与六个裸插头路径保留为前一轮对照，不能直接按图制作完整线束。

'''
md=md.replace('## 明确先装和后装',addition+'## 前一轮：三组线全部后装')
(OUT/'README.md').write_text(md)
stage_rows=''.join(f'<tr><td>{label}</td><td>{count}</td><td>PASS</td></tr>' for label,count in [('桥移动，上壳保持',37),('共同后移',57),('提起至装配台',253),('上壳回位',61)])
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI CAM 先装候选</title>
<style>body{{margin:0;background:#f5f8f8;color:#243d46;font:17px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1140px;margin:auto;padding:36px 24px}}h1{{font-size:32px;line-height:1.4}}h2{{font-size:24px}}section{{margin:32px 0;background:white;padding:24px;border-radius:14px}}img{{width:100%;height:auto}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ccd5d8;text-align:left}}a{{color:#147970}}.note{{border-left:4px solid #b87820;padding:12px 20px;background:#fff9ed}}nav{{display:flex;gap:20px;flex-wrap:wrap}}</style><main>
<p>独立装配研究 · 未应用主模型</p><h1>CAM 先装：身体阶段与六个插头路径已补查</h1>
<p class="note">完整带线装配仍未完成。后装导线、临时线尾、扎带、手部工具和供应商裁线图继续处理；这次没有更改打印结构或电路板。</p>
<section><h2>先把工序分清楚</h2><p>CAM 四根全长、共同 PH 插头与承重桥先装，H03 两根线保留。H01 / H02 / H04 的 12 根线和 6 个插头后装；122 件阶段源部件均参与检查。</p><img src="order.png" alt="CAM先装与三组身体线束后装的四步顺序，标明未完成范围"><table><tr><th>动作</th><th>有限位置</th><th>结果</th></tr>{stage_rows}</table><p>共408个有限位置通过；身体动作尚非连续验证。使用未应用的颈部与头托候选，主模型 M1.47 保持。</p></section>
<section><h2>六个后装插头可绕行接入</h2><p>其他插头保持最终位置，四根 CAM 线和 H03 导线也保留。六条自由移动路径的连续扫掠均通过0.3mm名义余量检查及结果复核；最初8mm插接段仅检查名义外形。</p><img src="connector_paths.png" alt="六个后装插头的YZ和XZ投影接入路径，二维重叠不是三维碰撞"><p class="note">插头空间分配仍为 ASSUMED。本轮未把后装的12根导线附在移动插头上，不能据此认定整束线已经能装进去。</p></section>
<section><h2>接下来补齐带线过程</h2><p>需要把三个身体线束连着插头送入，验证临时弯曲、长度与互相避让，再处理头部竖直线尾、扎带和其他跨关节线路。未完成项属于设计工作，不能统称为等待实物。</p><nav><a href="README.md">完整范围</a><a href="../dense.json">身体阶段结果</a><a href="../later_connections/grid_margin_approach/screen.json">六条路径</a><a href="../later_connections/grid_margin_approach/verification.json">余量复核</a><a href="http://127.0.0.1:58201/mechanical/studies/prearrival_finish/index.html">总进度</a></nav></section></main></html>'''
latest_section='<section><h2>后续复核：H02先装，H01/H04继续处理</h2><p>加上现有名义线长，H02与H04的原裸插头路径出现长度不足。H02改为更低的两线候选，在开敞机身内提前连接；两端插头与完整线形的201个装入位置、随后的408个身体位置和130个头部姿态通过。打印件与接口保持，完整线束仍未完成。</p><p><a href="../H02_preinstalled/index.html">查看新走向和线长复核</a>。H01/H04的10根后装导线、人手工具、固定与其他线束继续处理；参考线长不能用于裁线。</p></section>'
html=html.replace('<h1>CAM 先装：身体阶段与六个插头路径已补查</h1>','<h1>线长复核：H02先装，继续补齐带线工序</h1>')
html=html.replace('<section><h2>先把工序分清楚</h2>',latest_section+'<details><summary>前一轮工序和六个裸插头路径（对照）</summary><section><h2>前一轮：三组线全部后装</h2>')
html=html.replace('<section><h2>接下来补齐带线过程</h2>','</details><section><h2>接下来补齐带线过程</h2>')
html=html.replace('需要把三个身体线束连着插头送入，验证临时弯曲、长度与互相避让，再处理头部竖直线尾、扎带和其他跨关节线路。','需要完成H01/H04的带线送入，验证临时弯曲、长度与互相避让，再处理头部竖直线尾、扎带和其他跨关节线路。')
(OUT/'index.html').write_text(html)
review=str((OUT/'index.html').relative_to(P))
sp=P/'work_status.json';status=read(sp);status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['CAM_first_body_order']=dict(status='BLOCKED',scope='Finite full-CAM body order and continuous bare-plug access complete; attached deferred harnesses incomplete',
    finite_body_positions=408,finite_body_status='PASS',body_continuous='NOT_TESTED',deferred_harnesses=['H01','H02','H04'],
    later_bare_plug_paths=6,later_bare_plug_free_sweeps='PASS',free_sweep_nominal_margin_mm=.3,
    initial_mating_margin='NOT_TESTED',attached_deferred_harnesses='NOT_TESTED',later_yaw_over_stock='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,review=review)
status['CAM_first_body_order']['latest_order_variant']=dict(H02_preinstalled_candidate='PASS',open_deck_finite_positions=201,
    body_finite_positions=408,head_finite_positions=130,remaining_later_harnesses=['H01','H04'],
    remaining_later_conductors=10,review=str((h02dir/'index.html').relative_to(P)),main_applied=False)
for item in status['remaining']:
    if item['id']=='harness':
        item['detail']='四根CAM名义全长、上方暂存线尾及共同PH插头已建入。六个裸插头路径的局部结果保留；线长复核发现原H02/H04路径部分位置不够长。H02降低中段、提前接好的新候选通过201个开敞装入位置、408个身体位置、130个头部姿态；H01/H04的10根后装导线柔性送入仍未完成。后续头部装入与暂存线尾、扎带、人手工具、真实端子入壳、另7根跨关节线/FFC及完整连续顺序待完成。上部与颈部研究候选未应用，CAM内六角螺钉待确认，裁线图未放行。'
        item['evidence']=review
status['A8_harness_research'].update(latest_review=review,
    CAM_first_body_order_finite='PASS',CAM_first_body_order_finite_positions=408,
    CAM_later_bare_plug_paths='PASS',CAM_later_bare_plug_path_count=6,
    CAM_later_bare_plug_free_sweep_nominal_gap_mm=.3,
    CAM_later_attached_harnesses='NOT_TESTED',CAM_first_order_main_applied=False)
status['A8_harness_research'].update(H02_preinstalled_candidate='PASS',H02_open_deck_positions=201,
    CAM_later_harness_groups=['H01','H04'],CAM_later_harness_conductors=10)
sp.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
idx=P/'index.html';doc=idx.read_text();section=f'<section id="cam-first-body-order"><h2>H02先装：线长复核后的工序候选</h2><p><a href="{review}">查看线长问题和新走向</a>：H02较低走向提前连接，201个开敞装入位置、408个身体位置与130个头部姿态通过。H01/H04的10根后装导线及其余线束仍未完成；主模型保持，裁线图未放行。</p></section>'
doc=re.sub(r'<section id="cam-first-body-order">.*?</section>','',doc,flags=re.S);assert '</main>' in doc
idx.write_text(doc.replace('</main>',section+'</main>'))
pub=dict(status='PASS',scope='Evidence publication, not full cable assembly qualification',script_sha256=sha(SCRIPT),source_files=inputs,
    protected_sources=dense['protected_sources'],outputs={n:sha(OUT/n) for n in ['README.md','index.html','order.png','connector_paths.png']},
    body_finite_positions=408,bare_plug_paths=6,free_sweep_nominal_margin_mm=.3,full_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    H02_preinstalled_publication_sha256=sha(h02dir/'publication.json'),H02_open_deck_positions=201,remaining_later_harnesses=['H01','H04'])
(OUT/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n')
print('CAM_FIRST_REVIEW_PUBLISHED')
