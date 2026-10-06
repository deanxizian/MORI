"""Publish A8 receipt and bounded studies; preserve all main mechanical geometry."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
curves=json.loads((HERE/'central_uart_curves.json').read_text())
check=json.loads((HERE/'central_uart_source_check.json').read_text())
ends=json.loads((HERE/'central_exit_check.json').read_text())
receipt=json.loads((HERE/'receipt.json').read_text())
assert check['status']=='PASS' and ends['status']=='BLOCKED'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==check['source_blend_sha256']
bend=min(p['sampled_minimum_bend_radius_mm'] for p in curves['selected']['poses'])
gap=min(p['surface_gap_lower_bound_mm'] for p in check['interwire_checks'])
readme=f'''# A8 细线候选与中心通道局部复核

用户已确认 **供应商按图制作**，制作方式不再等待选择。本包是 M1.47 的独立研究，没有更换正式线材、PCB、打印件或装配动画，也不是线束加工图。

## 新资料已接收

硬件补交 [A8 报告](../../../../hardware/v1_2/head_harness_A8_20261003/README.md)；[接收记录](receipt.json)核对了 14 个来源和 537 个受保护文件。A8 补充 A7，不替换 C4、PHC1 或正式四板。

- PH 细线端子 **SPH-004T-P0.5S**：AWG32–28、绝缘外径0.5–0.9 mm。
- SH 端子 **SSH-003T-P0.2-H**：AWG32–28、外径0.4–0.8 mm。
- 两端共同外径范围0.5–0.8 mm。PHR-4胶壳和板座可保留作为研究方向；实际CAM插座完整厂牌/料号及插合面仍未确认。
- Alpha **2841/7** 原厂目录参考：30AWG、7/38、PTFE，外径0.5588–0.6604 mm。目录10D弯曲参考按最大外径为6.604 mm。完整订货后缀、价格、压接工艺、动态寿命尚未确认；不是已选采购料。
- GAM-050的ASSHSSH28K152是单根SH→SH线，其原BCD线外径仍未知，不能当作已配好的PH→SH四芯H06。

针序保持运动J5→CAM J11的1→1、2→2、3→3、4→4。第三根是CAM本地3V3电平参考，四根全部计入；不承担CAM主电源。

## 中心间隙：局部几何通过，完整线路仍受阻

![局部候选与端部限制](central_uart_review.png)

四根线分别沿现有中心环形间隙布置，中心半径6.8 mm；研究端点Z150与Z182 mm。每根中间段几何长度33.2 mm，13个yaw姿态长度计算保持，各根不是圆束中心线的代替。最小抽样曲率半径{bend:.3f} mm，大于本次采用的保守筛查值6.9342 mm。

对当前209实体的验证网格/已声明代理进行13 yaw×10 pitch组合姿态检查，共520个“导线×姿态”，未检出这段路径与源实体、14根固定线候选的干涉；与已有两组外圈用径向间隔下界另行检查。名义外部间隙要求0.3 mm；线间距离的全参数对界得到最小表面间隔下界{gap:.3f} mm。详见[曲线](central_uart_curves.json)与[源实体检查](central_uart_source_check.json)。这是有限姿态和名义实体检查，不是连续运动、实际保持位置或疲劳资格。

继续检查[八条直行延伸](central_exit_check.json)：下端从Z150向下，Z148之后的直行间隙界被Yaw_Base阻断；上端从Z182向上，Z188之后由Yaw_Reaction_Link阻断。报告在0.25 mm步长下记录首次保守间隙界不足，不能把Z147.75/Z188.25当作精确接触高度。这只排除了这八条直行路线；侧向转弯、进出口可达性、弯曲空间和真实装入尚未闭合。

外侧平面环的两个完整有限搜索池没有找到通过项，后续大搜索已终止，转而核对中心通道；[保留日志与终止范围](uart_planar_attempt.json)。另一种连续径向变化的盘绕曲线试了2835组，仍未找到通过项，见[记录](uart_spiral_loops.json)。这些失败均不等于证明所有外侧路线无解。

## 下一步与未解决项

1. 先检查中心通道两端是否能通过现有开口侧向进出，并保持所需弯曲半径；如果需要改变承重座/反力件，先做完整候选再交用户确认。
2. 定义实际上下固定点和四根线的定位方式，再连接运动板与CAM；目前没有套管、绑带、胶、导向件或插头后直段。
3. 俯仰活动段、其余7根跨yaw导线的端部连接、USB尾线与相机完整FPC仍未解决。
4. 按实际端子、插合视图和整条路线填写加工长度、分支与检验要求。**33.2 mm不能用作供应商下料长度。**

本研究不新增打印孔，不修改主模型；不联系供应商、不询价下单、不发布制造图。当前整套线束仍为BLOCKED，实物压接、装机与动态寿命为NOT_TESTED。
'''
(HERE/'README.md').write_text(readme)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · A8细线候选与局部通道</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f0f4f3;color:#263c36;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1150px;margin:auto;padding:32px 24px 70px}}h1{{line-height:1.4}}a{{color:#146c53}}.note{{background:#fff1d6;padding:18px 22px;border-radius:10px;border:1px solid #e1ca9d}}.pass{{background:#dcece3;padding:18px 22px;border-radius:10px}}img{{width:100%;height:auto;border:1px solid #c9d7d2;border-radius:8px;background:#fff}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #cfdbd5;padding:12px}}h2{{margin-top:30px}}code{{overflow-wrap:anywhere}}@media(max-width:700px){{th,td{{padding:7px;font-size:14px}}h1{{font-size:25px}}main{{padding:24px 16px}}}}</style>
<main><p><a href="../index.html">← 打样前工作状态</a> · <a href="../supplier_made_harness/index.html">已找到的CAD与压接线图</a></p>
<h1>A8：细线资料已核对，完整线束仍未闭合</h1>
<p class="note">供应商按图制作已经确定。本页是M1.47的独立研究；主模型、PCB与装配视频保持。没有最终下料长度或制造发布。</p>
<h2>可以减少中间接头的端子组合</h2>
<table><tr><th>项目</th><th>已确认资料</th><th>边界</th></tr>
<tr><td>PH细线端子</td><td>SPH-004T-P0.5S<br>AWG32–28，OD0.5–0.9 mm</td><td rowspan="2">两端共同外径0.5–0.8 mm；只是目录适配，不等于实际压接或CAM插合已验证。</td></tr>
<tr><td>SH端子</td><td>SSH-003T-P0.2-H<br>AWG32–28，OD0.4–0.8 mm</td></tr>
<tr><td>细线筛查参考</td><td>Alpha2841/7，OD0.5588–0.6604 mm<br>目录10D参考：最大6.604 mm</td><td>完整订货型号、压接、价格和连续弯折寿命未确认，未作采购替换。</td></tr></table>
<p>H06保留四根线，第三根是CAM本地3V3电平参考。针序和正式电路板均未改变。</p>
<h2>中间段通过，端部直行受阻</h2>
<img src="central_uart_review.png" alt="现有中心通道剖面及负60、零位、正60度四根候选线；中间段通过，两个端部直行受阻">
<p class="pass">局部几何：4根线各33.2 mm，最小抽样弯曲半径{bend:.2f} mm。130个头部组合姿态检查中，未检出这段曲线与当前实体、已有14根固定线候选的干涉；也检查了与两组外圈的间隔。</p>
<p class="note">下端直行遇到Yaw_Base，上端直行遇到Yaw_Reaction_Link。侧向进出、真实固定点、装入路径、俯仰段与插头连接尚未解决。33.2 mm只是局部几何长度，不能交供应商下料。当前检查也不验证连续运动寿命。</p>
<h2>仍需完成</h2><ol><li>核对两端侧向进出、转弯空间和实际装入；涉及结构改变时另提候选确认。</li><li>补齐端部固定、运动板到CAM整条路径、俯仰余量及逐线加工基准。</li><li>实际CAM插合面、端子压接工艺、其他分支和相机完整FPC资料。</li></ol>
<p><a href="README.md">完整说明</a> · <a href="receipt.json">A8接收记录</a> · <a href="central_uart_curves.json">四根曲线</a> · <a href="central_uart_source_check.json">源实体检查</a> · <a href="central_exit_check.json">端部限制</a> · <a href="delivery.json">交付检查</a></p>
<p><a href="../../../../hardware/v1_2/head_harness_A8_20261003/README.md">硬件A8与原厂资料</a> · <a href="../head_harness/index.html">此前头部线束研究</a></p></main></html>'''
(HERE/'index.html').write_text(html)

wp=PARENT/'work_status.json';w=json.loads(wp.read_text());old_detail=next(r['detail'] for r in w['remaining'] if r['id']=='harness')
detail='A8细线端子/外径已核对。4根UART的中心通道33.2mm局部段通过130个组合姿态检查，但上下端直行分别被Yaw_Base和Yaw_Reaction_Link阻断，侧向进出及固定未完成。14根身体固定线及两组外圈仍仅为独立候选；俯仰段、全路径、逐线加工长度与相机完整FPC未完成，未应用主模型。'
for r in w['remaining']:
    if r['id']=='harness':r.update(detail=detail,evidence='harness_A8/index.html')
w['updated_utc']=datetime.now(timezone.utc).isoformat()
w['prearrival_wire_addendum'].update(A8_receipt='PASS',A8_review='harness_A8/index.html',
    A8_formal_wire_replacement=False,UART_central_local_segment='PASS',
    UART_central_endpoint_straight_extensions='BLOCKED',complete_UART_harness='BLOCKED')
w['A8_harness_research']={'scope':'Independent fine-wire catalogue receipt and central 32 mm-high passage only',
    'source_receipt':'harness_A8/receipt.json','local_source_checks':'harness_A8/central_uart_source_check.json',
    'endpoint_checks':'harness_A8/central_exit_check.json','review':'harness_A8/index.html',
    'main_geometry_changed':False,'final_harness_drawing':'BLOCKED'}
wp.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')

parent_page=PARENT/'index.html';s=parent_page.read_text()
section='<section id="harness-A8-update"><h2>A8细线候选：局部通道复核</h2><p><a href="harness_A8/index.html">端子资料、四根线与端部限制</a>：中心间隙的局部活动段检查通过，上下进出仍未解决；未修改主模型，也没有最终下料长度。</p></section>'
if 'id="harness-A8-update"' not in s:s=s.replace('<main>','<main>'+section,1)
s=s.replace(old_detail,detail)
parent_page.write_text(s)
headpage=PARENT/'head_harness/index.html';s=headpage.read_text()
if 'id="A8-central-update"' not in s:
    block='<section id="A8-central-update"><h2>后续A8：细线与中心间隙</h2><p><a href="../harness_A8/index.html">四根UART细线的局部候选与端部限制</a>已有新结果：中间段通过，完整进出与俯仰仍未完成。下列外圈试算保留为此前研究，不代表最终方案。</p></section>'
    s=s.replace('<main>','<main>'+block,1)
headpage.write_text(s)
supplier=PARENT/'supplier_made_harness/index.html';s=supplier.read_text()
if 'id="A8-wire-update"' not in s:
    s=s.replace('<main>','<main><section id="A8-wire-update"><h2>硬件已补交A8细线资料</h2><p><a href="../harness_A8/index.html">PH/SH细线端子与通道复核</a>已接收。以下JST预压接线仍作为来源参考，不能替代最终MORI线束图。</p></section>',1)
supplier.write_text(s)
print('A8_REVIEW_PUBLISHED')

# Preserve the later endpoint investigation when republishing the original page.
if (HERE/'central_body_escape_graph.json').is_file():
    import runpy
    runpy.run_path(str(HERE/'publish_endpoint_review.py'), run_name='__main__')
