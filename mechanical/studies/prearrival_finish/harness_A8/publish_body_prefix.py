"""Publish the verified body-to-yaw candidate without treating it as CAM fit."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'body_prefix_v2';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pack=read(OUT/'packing.json');motion=read(OUT/'body_to_yaw_motion.json')
other=read(OUT/'other_loop_coexistence.json');preview=read(OUT/'preview_manifest.json')
assert all(d['status']=='PASS' for d in [pack,motion,other,preview])
assert sha(ROOT/'mechanical/mori_v1_2.blend')==motion['source_blend_sha256']
table=[]
for p in pack['selected']:
    r=next(q for q in motion['rows'] if q['pin']==p['pin'] and q['yaw_deg']==0)
    table.append(f'| Motion J5 #{p["pin"]} | {p["azimuth_deg"]}° | {p["analytic_prefix_length_mm"]:.2f} | {r["analytic_partial_length_mm"]:.2f} |')
detail=f'H06四根UART线已从Motion J5分配出线面接到偏航上方暂存点；四线成组、209源实体/代理、29个插头包络及14根静态线的130头部姿态检查通过，四线间隙保守下界{motion["minimum_pair_surface_gap_bound_mm"]:.3f}mm。与另外两组局部Yaw线束包络也通过。尚缺固定、穿线/带线拆装、俯仰段与CAM连接，J2打印改动未采用；主模型保持M1.47。'
md=f'''# H06：身体端四线已接通到偏航段

**这是独立候选，整体线束仍为 BLOCKED。主模型 M1.47 未改，不能据此下料或打印。**

{detail}

## 具体完成的设计

四根线保留 Motion J5 的原针号与2mm针距，保留5mm轴向出线分配。随后使用R7起弯、相切圆弧/直线和降高过渡，分别到达中央偏航段的225°、135°、315°和45°入口。没有交换电气针序，没有挪动板卡或缩小硬件。

采用0.6604mm最大外径研究值，来自此前Alpha2841/7候选；尚未采购或冻结制线用料。端子真正出线面仍为分配值，真实SH/CAM配套接口仍待核实。

![俯视四线与板卡](body_prefix_top.png)

俯视图为看清走线，隐藏了承重桥、转台和反力件；电源板、运动板及插头包络保留。琥珀色是候选/预留物。图中的线交叉属于不同高度，间隙已按三维曲线检查，不能仅看二维投影判断。

![保留承重桥的斜后视图](body_prefix_rear.png)

## 检查结果与边界

| 项目 | 结果 | 覆盖范围 |
|---|---|---|
| 四根身体端线一起布置 | PASS | 全部6对，保留原针序；不是只找4条各自可走的线 |
| 接上已有偏航曲线 | PASS | 13个Yaw×10个Pitch，520个线/姿态实例，对209源实体或既有代理 |
| 29个对插包络、14根既有静态线 | PASS | XT30使用17.9mm高度上界；5.9mm线端厚度仍是显式分配 |
| 四线互相间隙 | PASS | 78项检查，保守下界{motion['minimum_pair_surface_gap_bound_mm']:.3f}mm ≥ 0.3mm项目分配 |
| 非相邻线段回绕 | PASS | 52项检查；相邻2mm弧长由连续曲率形状单独约束 |
| 与另两组Yaw局部预留环 | PASS | 104项，间隙下界{other['minimum_surface_gap_lower_bound_mm']:.3f}mm；不等于另外7根线已完成 |
| 线束固定、供应商穿线及带线拆装 | NOT_TESTED | 不能拿装后形状代替装配过程 |
| 上方暂存点到CAM、完整俯仰段 | BLOCKED | 当前图中上端为明确的暂存端，没有假装已经接入板卡 |

圆弧身体段最小中心线半径7mm；偏航段沿用既定有限姿态曲线。这里是名义几何复核，不是运动寿命、受力变形或抗磨验证。

## 长度基准已建立，但不是加工长度

| 原针号 | 入口方位 | 身体段中心线 / mm | 到偏航上方暂存点 / mm |
|---|---:|---:|---:|
{chr(10).join(table)}

上述长度从分配的塑壳出线面算起，未含端子内部、完整CAM/俯仰段、固定及拆装松量、公差和剥线。禁止作为逐线裁切长度。四根线的各自长度在13个Yaw样本中保持；这也不等于真实柔性线束不会受拉。

## 还需要现在完成的工作

1. 身体端固定/应力释放，以及松开固定后的插拔和整机装配顺序。
2. 裸端子实际穿入与随后的柔线；旧J2参考端子扫掠不能直接代替本次完整带线安装。
3. 俯仰段、CAM配对接口和其余7根活动导线；焊点、热缩管与真实出线空间也要纳入。
4. 两件J2候选打印件的局部壁厚/承力复核，再向用户提交具体结构确认。未增加新零件，不代表可以跳过这一检查。

## 可复查文件

- [独立可编辑Blender](H06_BODY_TO_YAW_CANDIDATE_NOT_ADOPTED.blend)；[预览来源清单](preview_manifest.json)
- [四线成组选择](packing.json)；[130姿态及三维间隙](body_to_yaw_motion.json)；[曲线数据](body_to_yaw_curves.npz)
- [与其他两组局部环的共存检查](other_loop_coexistence.json)
- [实际高度带投影](corridors.png)；[独立路线候选池](dubins_pools.json)
- [命令和版本](commands.json)；[原厂插合数据](../amass_mating/index.html)

主模型SHA256：`{motion['source_blend_sha256']}`。硬件文件只读。没有更新主STL或装配视频，没有发布制造数据。
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>H06四线身体端 · MORI独立候选</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,sans-serif;max-width:1120px;margin:28px auto;padding:0 24px 50px;background:#f3f6f5;color:#2d4047}}a{{color:#087484}}h1{{font-size:30px}}h2{{font-size:23px;margin-top:30px}}img{{width:100%;border-radius:8px}}.note{{background:#fff0d8;border-left:4px solid #bf7e23;padding:14px 18px}}.pass{{background:#e5f0e6;padding:14px 18px}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #cbd8d9;text-align:left}}</style>
<p><a href="../index.html">← A8线束设计与原厂资料</a></p><h1>四根线已从身体接到偏航段</h1>
<p class="note">独立候选 · 主模型M1.47未改 · 尚未固定，也未接到CAM。完整线束仍为BLOCKED，不是加工图。</p>
<p class="pass">{detail}</p><h2>俯视走线</h2><img src="body_prefix_top.png" alt="四根UART候选线保留原运动板针序，绕开已有线束后分别进入偏航段">
<p>这一视图隐藏承重桥、转台和反力件；不同高度的线可能在图上交叉，三维间隙已独立检查。琥珀色为候选导线及插头包络。</p>
<h2>保留结构的斜后视图</h2><img src="body_prefix_rear.png" alt="保留承重桥与转台后的身体到偏航候选线束">
<table><tr><th>已经检查</th><th>结果</th></tr><tr><td>4根线成组、全部6对间隙</td><td>PASS</td></tr><tr><td>209源实体/代理、29个对插包络、14根静态线</td><td>130个头部姿态；520个线/姿态实例PASS</td></tr><tr><td>四线间隙保守下界</td><td>{motion['minimum_pair_surface_gap_bound_mm']:.3f}mm</td></tr><tr><td>与另外两组局部Yaw环</td><td>104项PASS；另外7根活动线尚未完整设计</td></tr></table>
<h2>上端暂存，不能按这些长度下料</h2><p>上方竖直线段到Z206mm暂存点结束，俯仰段与CAM实际插头还没连接。这里的逐线长度只用于继续设计，未含端子内部、固定、拆装松量及剥线。</p>
<h2>接下来仍需处理</h2><p>固定与应力释放、带线穿入/拆装、俯仰段和其余活动线、实际插头与热缩管、J2改动后的局部壁厚。两件打印结构的候选改动尚未请求正式应用。</p>
<p><a href="README.md">完整范围与长度基准</a> · <a href="H06_BODY_TO_YAW_CANDIDATE_NOT_ADOPTED.blend">独立可编辑Blender</a> · <a href="body_to_yaw_motion.json">姿态检查</a> · <a href="packing.json">四线成组检查</a> · <a href="other_loop_coexistence.json">与其他预留环检查</a> · <a href="commands.json">命令记录</a></p></html>'''
(OUT/'index.html').write_text(html)
blender='/Applications/Blender.app/Contents/MacOS/Blender --background '
rootcmd='mechanical/studies/prearrival_finish/harness_A8/'
commands=[blender+'mechanical/mori_v1_2.blend --python-exit-code 1 --python '+rootcmd+s+'.py' for s in ['inspect_body_prefix_space','plan_body_dubins','check_body_prefix_motion','render_body_prefix']]
commands += [blender+'--python-exit-code 1 --python '+rootcmd+s+'.py' for s in ['pack_body_prefix','check_prefix_other_loops']]
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+rootcmd+s+'.py' for s in ['plot_body_prefix_space','publish_body_prefix','verify_delivery']]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,
    'versions':{'blender':'5.2.2 LTS d13f752e3b9c','plot_python':'3.12.14'},
    'corrected_script_errors':['Inspection helper path was overwritten by shared bootstrap; unique INSPECT_HELPER retained.',
      'Render mesh function was shadowed by bootstrap mesh data; explicit create_review_mesh import used.'],
    'main_model_applied':False},ensure_ascii=False,indent=2)+'\n')
sp=PARENT/'work_status.json';state=read(sp);old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='harness_A8/body_prefix_v2/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/body_prefix_v2/index.html',
    body_four_wire_packing='PASS',body_to_yaw_source_motion='PASS',body_to_yaw_pair_gap_lower_bound_mm=motion['minimum_pair_surface_gap_bound_mm'],
    body_to_yaw_other_local_loops='PASS',body_to_yaw_anchoring='NOT_TESTED',body_to_yaw_installation='NOT_TESTED',
    body_prefix_after_mating_update='PASS',J2_body_four_wire_prefix='PASS',
    early_single_cubic_body_prefix_family='BLOCKED',AMASS_upper_mates_body_to_yaw='PASS',
    complete_UART_harness='BLOCKED',J2_applied=False)
state['updated_utc']=datetime.now(timezone.utc).isoformat();sp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for path,href in [(HERE/'index.html','body_prefix_v2/index.html'),(PARENT/'index.html','harness_A8/body_prefix_v2/index.html')]:
    text=path.read_text();block=f'<section id="threading-update"><h2>最新：四线身体端已接通偏航段</h2><p>{detail}</p><p><a href="{href}">查看三维候选与检查范围</a>。下方保留早期研究记录。</p></section>'
    text=re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S).replace(old,detail);path.write_text(text)
path=HERE/'README.md';text=path.read_text();note='<!-- body-prefix-latest:start -->\n**最新进展：**'+detail+'\n\n[四线身体端三维候选](body_prefix_v2/index.html)。下文失败结果保留为早期有限家族记录。\n<!-- body-prefix-latest:end -->'
if '<!-- body-prefix-latest:start -->' in text:text=re.sub(r'<!-- body-prefix-latest:start -->.*?<!-- body-prefix-latest:end -->',note,text,flags=re.S)
else:text=text.split('\n',1)[0]+'\n\n'+note+'\n'+text.split('\n',1)[1]
path.write_text(text)
print('BODY_PREFIX_REVIEW_PUBLISHED_MAIN_UNCHANGED')
