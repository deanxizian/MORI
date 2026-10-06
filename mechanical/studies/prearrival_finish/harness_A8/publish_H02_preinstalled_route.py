"""Publish the source-length audit and verified independent H02 order variant."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,html
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=BASE/'H02_preinstalled';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
assert '--visual-reviewed' in sys.argv
screen=read(OUT/'screen.json');verified=read(OUT/'verification.json');insertion=read(OUT/'open_deck_insertion.json');plot=read(OUT/'plot.json')
audit_path=BASE/'later_connections/length_budget/audit.json';audit=read(audit_path)
for r in [screen,verified,insertion,plot,audit]:assert r['status']=='PASS'
assert verified['screen_sha256']==sha(OUT/'screen.json') and verified['wire_solids_sha256']==sha(OUT/'wire_solids.json')
assert sum(r['checked_positions'] for r in verified['body_stages'])==408
assert verified['head_poses']==130 and not verified['head_solid_intersections']
assert len(insertion['rows'])==201 and all(r['status']=='PASS' for r in insertion['rows'])
scripts=['screen_H02_preinstalled_route.py','verify_H02_preinstalled_route.py','verify_H02_open_deck_insertion.py','plot_H02_preinstalled_route.py','check_CAM_later_harness_length_budget.py']
for r,n in zip([screen,verified,insertion,plot,audit],scripts):assert r['script_sha256']==sha(A8/n)
for p,h in verified['protected_sources'].items():assert sha(ROOT/p)==h
for r in [verified,insertion,plot,audit]:
    for p,h in r['source_files'].items():assert sha(ROOT/p)==h,p
for p,h in plot['outputs'].items():assert sha(OUT/p)==h
group={r['harness']:r for r in audit['rows']}
assert group['H02']['necessary_length_coordination_status']=='BLOCKED'
assert group['H04']['both_exterior_status']=='BLOCKED'
input_paths=[OUT/n for n in ['screen.json','verification.json','wire_solids.json','open_deck_insertion.json','plot.json']]+[audit_path]+[A8/n for n in scripts]
inputs={str(p.relative_to(ROOT)):sha(p) for p in input_paths}
body=f'''# H02 提前连接：线长复核与工序调整

**H02 的两根线可以采用较低的新候选走向，在开放的身体内先接好，再装 CAM 与承重桥。**
主模型和硬件未改。这是独立的名义几何候选，完整线束仍未完成。

## 为什么调整

前一轮六个插头的路径检查没有带上导线。加入现有名义线长后：

| 线束 | 只移动一端的线长必要条件 | 两端到原外部位置 | 后续处理 |
|---|---|---|---|
| H01 | 两端各自移动都未检出长度不足 | 未检出长度不足 | 继续检查带线过程 |
| H02 | 两端各自移动都存在长度不足 | 这个位置本身满足，但有限协调进度未找到可行顺序 | 改为开敞机身内先装 |
| H04（IMU） | 移动运动板端时部分线不够；只移动 IMU 端满足此必要条件 | 部分线不够，最大差约40.44mm | 另改装配工序或接入路径 |

必要长度下界采用两端各5mm直段加直段末端距离。正余量不证明弯曲与碰撞通过；
负余量只排除测试位置和当前候选长度，**不证明线束无法安装**。
两端同步使用每端81个采样进度；没有穷尽所有柔性动作。

## H02 新候选

原 motion_J2 / power_J13 接口、针序、5mm端后直段均保持。只调整两根候选导线，
圆弯半径保持5.08mm、线径1.016mm；仍为未选定采购的 Alpha6711 参考线材。
参考路径长度约50.40 /53.98mm，不含最终端接、制造与维修余量，不能发给供应商裁线。

![前后路线对比](comparison.png)

| 本轮检查 | 结果与范围 |
|---|---|
| 静态两根 H02、209件源零件、29个插头空间分配、其他12根身体导线 | PASS，名义间隙0.3mm；出口与实际配套仍未确认 |
| H02 两线互相间隙 | PASS，膨胀胶囊几何下界约{verified['pair']['inflated_capsule_gap_lower_bound_mm']:.3f}mm |
| 两个插头与完整H02线形，从上方落入开敞机身 | 201个有限位置PASS，保留H03；人手和临时保持形状未验证 |
| H02/H03已经连接，CAM四根全长与承重桥随后装入 | 408个有限位置PASS；H01/H04后装 |
| 头部130个组合姿态 | 没检出新增实体相交；不是连续运动证明 |

建议工序：开放机身内先装 H03、H02 → 安装 CAM 四线与承重桥 → 再处理 H01、H04。
H03自己的既有工序并未由本次重新认证。研究继续使用未应用的颈部与头托候选。

## 仍需完成

H01/H04带线装入、临时线尾处理、扎带与固定、人手/工具、其他跨关节线、FFC，
以及最终供应商分支与长度图仍是设计工作。H02的实际线材/端子、容差和实物弯曲保持另待确认。
没有变更 PCB、打印件、主模型或主装配动画，没有采购或制造放行。

[线长检查](../later_connections/length_budget/audit.json) · [H02候选](screen.json) · [实体与运动检查](verification.json) · [开敞机身装入](open_deck_insertion.json)
'''
(OUT/'README.md').write_text(body)
rows=''.join('<tr><td>'+html.escape(r['harness'])+'</td><td>'+html.escape(r['from_only_status'])+'</td><td>'+html.escape(r['to_only_status'])+'</td><td>'+html.escape(r['both_exterior_status'])+'</td></tr>' for r in audit['rows'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI H02 先装与线长复核</title>
<style>body{{margin:0;background:#f3f7f7;color:#23414a;font:17px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1150px;margin:auto;padding:30px 22px}}section{{background:white;padding:24px;border-radius:12px;margin:24px 0}}h1{{font-size:30px}}h2{{font-size:23px}}img{{width:100%}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d5dfdf}}a{{color:#107d79}}.note{{border-left:4px solid #b67622;background:#fff6e9;padding:15px}}nav{{display:flex;gap:20px;flex-wrap:wrap}}</style><main>
<p>独立研究 · M1.47 主模型保持</p><h1>H02 提前接好，减少后装绕行</h1><p class="note">完整线束仍未完成。这次解决 H02 的候选走向与部分工序；线长是几何参考，不是裁线单。</p>
<section><h2>先纠正裸插头路径的边界</h2><p>把已有导线接上后，部分路径超出现有名义长度。表中的 PASS 仅表示必要长度下界没有超限，不代表导线已经能通过结构；BLOCKED 仅针对保存的路径和该长度。</p><table><tr><th>线束</th><th>只移动起端</th><th>只移动末端</th><th>两端均到原外部位置</th></tr>{rows}</table><p>H02 两端外部位置本身够长，但81×81个有限协调进度中没有找到可行顺序；H04 两端外移时最多差约40.44mm。因此继续用原裸插头路径不能放行整束装配。</p></section>
<section><h2>H02 保持接口，降低中段</h2><img src="comparison.png" alt="H02原曲线灰色虚线与两个较低的新曲线对比，端点固定"><p>接口针序、两端5mm直段和R5.08mm圆弯保持，不改结构。参考路径约50.40 /53.98mm；端接、实物公差与维护余量仍需确定。</p><p>209件源零件、29个插头预留及其他12根身体导线参与静态检查。H02两线间隙保守下界约{verified['pair']['inflated_capsule_gap_lower_bound_mm']:.3f}mm。</p></section>
<section><h2>候选顺序与复核</h2><p>先在开敞机身装H03、H02，再装CAM四线与承重桥，H01/H04最后处理。H02完整线形连同两端插头的竖直装入通过201个有限位置；随后身体工序408个位置通过，130个头部姿态未检出新增实体相交。</p><p class="note">仍缺 H01/H04 带线工序、固定与扎带、人手工具、后续头部线尾和其余线束。研究使用未采用的颈部/头托候选，有限位置检查不等于连续或实物装配通过。</p><nav><a href="README.md">完整说明</a><a href="../later_connections/length_budget/audit.json">线长证据</a><a href="verification.json">实体与运动检查</a><a href="open_deck_insertion.json">开敞装入</a><a href="../review/index.html">此前工序对照</a></nav></section></main></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Publication of length audit and H02 independent candidate, not complete harness assembly',
    script_sha256=sha(SCRIPT),source_files=inputs,protected_sources=verified['protected_sources'],
    outputs={p:sha(OUT/p) for p in ['README.md','index.html','comparison.png']},
    H02_body_positions=408,H02_open_deck_positions=201,H02_head_positions=130,
    H02_preinstalled_candidate='PASS',remaining_later_harnesses=['H01','H04'],remaining_later_conductors=10,
    original_length_conflicts=['H02','H04'],full_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    generated_utc=datetime.now(timezone.utc).isoformat())
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('H02_REVIEW_PUBLISHED')
