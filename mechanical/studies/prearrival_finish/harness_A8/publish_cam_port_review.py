"""Publish sourced CAM mate allocation, failed combinations and lower staging."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
HERE=Path(__file__).resolve().parent;OUT=HERE/'cam_pitch_port';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['mating_allocation','departure_screen','coexistence_screen','departure_v2/screen',
       'lower_staging/coexistence_screen','render_manifest']
data={n:read(OUT/(n+'.json')) for n in names}
assert data['mating_allocation']['status']==data['departure_screen']['status']==data['lower_staging/coexistence_screen']['status']=='PASS'
assert data['coexistence_screen']['status']==data['departure_v2/screen']['status']=='BLOCKED'
assert data['render_manifest']['source_script_sha256']==sha(HERE/'render_cam_departure.py')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==data['mating_allocation']['source_main_sha256']
source_record={'updated_utc':datetime.now(timezone.utc).isoformat(),
    'catalogue':{'url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
        'local_source':'hardware/v1_2/head_harness_evidence_20261003/sources/JST_SH.pdf',
        'sha256':sha(ROOT/'hardware/v1_2/head_harness_evidence_20261003/sources/JST_SH.pdf'),
        'used_pages':{'1':'Side-entry assembled reference length6.25mm','2':'SHR-04V-S body5x2.8x5mm, pitch1mm','3':'SM04B-SRSS-TB axial body4.25mm'}},
    'official_CAM_schematic':'https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-XXXX-schematic.pdf',
    'CAM_exact_manufacturer_and_MPN':'BLOCKED; public schematic describes generic SH1.0 4P, not confirmed JST part',
    'JST_CAD_listing':'https://www.jst-mfg.com/product/index.php?lang=2&series=231',
    'JST_CAD_access_result':'Download links lead to company/name/address/phone/email submission and email delivery. No data submitted; CAD not downloaded.',
    'gated_links':['https://www.jst-mfg.com/product/index.php?doc=2&filename=SHR-04V-S.zip&series=231&type=10',
        'https://www.jst-mfg.com/product/index.php?doc=2&filename=SM04B-SRSS-TB.zip&series=231&type=10'],
    'uses_only_public_catalogue_for_geometry':True,'supplier_contacted':False,
    'no_actual_mating_or_purchase_qualification':True}
(OUT/'source_update.json').write_text(json.dumps(source_record,ensure_ascii=False,indent=2)+'\n')
co=data['lower_staging/coexistence_screen'];gaps={r['family']:r['minimum_surface_gap_bound_mm'] for r in co['families']}
detail=('已从JST原厂目录推导CAM候选插头外露2mm，补查插头、5mm出线直段及6mm拔出行程。'
    'CAM端向左/向前两组R7以上出线通过源实体姿态检查；与旧Z206暂存线段相交，保持旧分段的30种后续尝试也未通过。'
    '把未定型的偏航分段点降至Z193后，两段之间130姿态、4160组合检查通过。中间活动线段仍未连接，不能给最终下料长度；主模型未改。')
md=f'''# CAM接线端：官方尺寸与条件性出线研究

**整体线束 BLOCKED。以下是独立路线研究，不是采购替换、最终线束图或主模型更新。**

## 原厂资料能补齐什么

- [JST SH公开目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)：SHR-04V-S无侧凸版本5×2.8×5 mm、1 mm间距；SM04B-SRSS-TB轴向长度4.25 mm；侧插配对长度参考6.25 mm。因此，以共同后端基准推导的前侧外露长度是2 mm。
- [JST PH公开目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)和[现有逐料号压接查询](../TOOLING_DETAILS.md)：提供两端端子、适用线径、配套工具和工艺参考。供应商按图加工的方式已确定，不需要用户代替检索这些公开资料。
- [微雪原理图](https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-XXXX-schematic.pdf)只描述SH1.0 4P，没有完整厂牌/料号。本研究采用JST目录尺寸作条件性分配，**不能据此断言CAM实际装的是这只JST插座**。
- [JST CAD列表](https://www.jst-mfg.com/product/index.php?lang=2&series=231)列有相关STEP/2D数据，但链接进入个人和公司资料提交、邮件发送流程。本次没有提交资料或取得受该流程限制的CAD；使用的是公开目录。[来源记录](source_update.json)。

## 条件模型和检查边界

以已有官方照片定位的CAM UART口为基准，插头出线面约为Z214.600 mm；X/Y及实际插合位置仍属ASSUMED。
CAD里的橙色块是条件性插头包络；四色仅表示四个几何槽位，**不代表已核实的实物针号或线色**。
原有电气1→1等逻辑针序保持；不擅自指定插合面pin1。

检查只排除了CAM自己的UART配合件，保留PCB与其余元件。重构CAM实体与原检查缓存体积对称差0.004664 mm³，小于预先设定0.02 mm³数值门槛。
130个组合姿态下，名义插头和四根5 mm直段未检出材料相交；零位6 mm直线拔出扫掠也未检出相交。插头与PCB面按目录参考贴合，**未证明0.3 mm装配间隙或实际公差 fit**。
照片定位±0.4 mm、凸出高度±0.5 mm没有包含在这次名义检查中，实际配套、插入深度、卡扣和压接仍待确认。

## 两个CAM端候选

![向左：四个嵌套圆弧](left_departure.png)
![向前：四个平行圆弧](forward_departure.png)

为看清端子与线，图片只显示CAM，其他支架暂时隐藏；几何检查使用全部源实体。完整场景保存在[可编辑比较文件](comparison.blend)。

| 局部形状 | 左转 | 前转 |
|---|---:|---:|
| 首段直线 | 5 mm | 5 mm |
| 圆弧中心线半径 | 7/8/9/10 mm | 4根均7 mm |
| 后段直线 | 4 mm | 4 mm |
| 四根线外表面间隙下界 | 0.3294 mm | 0.3294 mm |
| 本段名义长度 | 约20.00–24.71 mm | 每根约20.00 mm |

源实体及29个对插分配、14根静态线的130个相对姿态检查通过。这只完成CAM端一段，表中的长度不能用作供应商裁切长度。

## 同时装入后发现的问题，以及本次调整

两种端部候选分别看都避开实体，但与此前到Z206的四根偏航暂存线一起检查时相交：[旧组合失败记录](coexistence_screen.json)。固定原Z206分段，改圆弧顺序/半径/方向的30种尝试仍未找到满足全部条件的方案：[保留记录](departure_v2/screen.json)。这不是所有布线形式无解的证明。

Z206原本是**临时路线终点，不是硬件或已完成的固定点**。本次研究把其末尾13 mm竖直段截去，改以Z193为下一段活动线的暂定起点；每个新点严格位于旧直线上，不移动板卡、接头、支架或既有通道，不改变已通过的下面那段路线。

采用较低分段后，两侧仍彼此分离：130姿态×4CAM槽位×4偏航线×2方案，共4160组检查通过；左转最小间隙下界{gaps['left']:.3f} mm，前转{gaps['forward']:.3f} mm。[完整检查和截取依据](lower_staging/coexistence_screen.json)。
**这尚未连接成一根线。**两段之间的恒长活动线、固定点、装入顺序、其余活动线和FPC仍需完成。不能把分开的两段无碰撞说成整束已完成。

## 文件和复查

- [插头与直出段检查](mating_allocation.json) · [局部出线](departure_screen.json) · [临时分段调整](lower_staging/coexistence_screen.json)
- [图像来源](render_manifest.json) · [复现命令](commands.json) · [发布清单](review_manifest.json)
- [J3M通道上缘清理](../assembly_feed_v3/open_mouth/index.html) · [项目状态](../../index.html)

主模型SHA256：`{data['mating_allocation']['source_main_sha256']}`。硬件文件、针序、STL、装配视频不变；没有订单或制造发布。
'''
(OUT/'README.md').write_text(md)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM接线端资料与路线</title>
<style>body{{font:16px/1.8 system-ui,sans-serif;background:#f2f5f5;color:#293f46;max-width:1100px;margin:30px auto;padding:0 24px 50px}}a{{color:#07737e}}.note{{padding:16px 20px;background:#fff0d7}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #ccd7d8}}@media(max-width:700px){{.pair{{grid-template-columns:1fr}}}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">完整项目状态</a></p><h1>CAM接线端：先用原厂尺寸解决名义空间</h1>
<p class="note">独立候选，未应用主模型。完整线束仍为BLOCKED；两段之间的活动线尚未连接，不能用于下料。</p>
<p>已查到<a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH原厂目录</a>：无侧凸SHR-04V-S为5×2.8×5 mm；侧插配对参考长度6.25 mm，插座轴向4.25 mm，推导前侧外露2 mm。<a href="source_update.json">来源与CAD获取限制</a></p>
<p>微雪原理图只写SH1.0 4P，实际厂牌/料号仍未确认。橙色是条件性插头包络，四色仅为几何槽位。图片只显示CAM，支架隐藏；检查使用全部源实体。</p>
<div class="pair"><figure><img src="left_departure.png" alt="条件性SH插头，四根线向左圆弧出线"><figcaption>左转：R7/8/9/10 mm</figcaption></figure><figure><img src="forward_departure.png" alt="条件性SH插头，四根线向前平行圆弧出线"><figcaption>前转：四根均R7 mm</figcaption></figure></div>
<h2>通过了哪些，哪里还没完成</h2><table><tr><th>检查</th><th>结果</th></tr><tr><td>名义插头、5 mm直出段、零位拔出</td><td>PASS；实际插合、公差和照片误差未验证</td></tr><tr><td>两种端部线形与源实体</td><td>PASS；130个组合姿态，线间净空下界约0.329 mm</td></tr><tr><td>与旧Z206暂存段同时放入</td><td>BLOCKED；两条候选均相交，保留失败记录</td></tr><tr><td>改用Z193临时分段后，两段共存</td><td>PASS；4160组合，左转最小间隙{gaps['left']:.3f} mm、前转{gaps['forward']:.3f} mm</td></tr><tr><td>两段间活动线、固定点、整束装入、最终长度</td><td>NOT_TESTED；仍需完成数字设计</td></tr></table>
<p>Z206是路线暂存终点，不是硬件。只在独立研究中截短末尾13 mm竖直线，板卡和打印件保持。两段仍未相连，不能称为完整线束。</p>
<p><a href="README.md">完整说明</a> · <a href="comparison.blend">可编辑比较场景</a> · <a href="mating_allocation.json">插头检查</a> · <a href="departure_screen.json">局部线形</a> · <a href="coexistence_screen.json">旧组合失败</a> · <a href="departure_v2/screen.json">30种后续尝试</a> · <a href="lower_staging/coexistence_screen.json">低位分段检查</a> · <a href="render_manifest.json">图像来源</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">发布清单</a></p>
<p><a href="../assembly_feed_v3/open_mouth/index.html">J3M穿线出口清理</a> · <a href="../TOOLING_DETAILS.md">端子压接资料</a></p></html>'''
(OUT/'index.html').write_text(page)
base='"/Applications/Blender.app/Contents/MacOS/Blender" -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/'
commands=[base+s+'.py' for s in ['check_cam_uart_mating_allocation','plan_cam_uart_departure','check_cam_departure_coexistence','plan_cam_uart_departure_v2','check_cam_lower_staging']]
commands.append(base.replace('mechanical/mori_v1_2.blend','mechanical/studies/prearrival_finish/harness_A8/assembly_feed_v3/open_mouth/cleaned/candidate.blend')+'render_cam_departure.py')
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'reproduction_commands_in_separate_processes':commands,
    'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':'3.12.14'},
    'first_run_note':'First connector test repeated same-body transforms and created near-contact numerical overlaps. Exact identity for co-moving parts fixes that arithmetic; no collision threshold was relaxed. Initial results preserved in history_first_relative_transform.'},ensure_ascii=False,indent=2)+'\n')
sp=PARENT/'work_status.json';state=read(sp);old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='harness_A8/cam_pitch_port/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/cam_pitch_port/index.html',
    CAM_catalogue_mate_nominal_allocation='PASS',CAM_pitch_fixed_departure='PASS',
    CAM_old_Z206_combination='BLOCKED',CAM_lower_Z193_disjoint_halves='PASS',
    CAM_actual_connector='BLOCKED',CAM_yaw_pitch_service_loop='NOT_TESTED',CAM_route_applied=False)
state['updated_utc']=datetime.now(timezone.utc).isoformat();sp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for path,href in [(HERE/'index.html','cam_pitch_port/index.html'),(PARENT/'index.html','harness_A8/cam_pitch_port/index.html')]:
    text=path.read_text();block=f'<section id="threading-update"><h2>最新：CAM接线端资料与两段线的衔接研究</h2><p>{detail}</p><p><a href="{href}">查看原厂尺寸、两种出线与未完成项</a>。下方保留历史阶段。</p></section>'
    assert '<section id="threading-update">' in text
    path.write_text(re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S).replace(old,detail))
path=HERE/'README.md';text=path.read_text();note='<!-- coupled-feed-latest:start -->\n**最新进展：**'+detail+'\n\n[CAM接线端与低位分段研究](cam_pitch_port/index.html)。\n<!-- coupled-feed-latest:end -->'
path.write_text(re.sub(r'<!-- coupled-feed-latest:start -->.*?<!-- coupled-feed-latest:end -->',note,text,flags=re.S))
manifest={'status':'PASS','scope':'Source-backed conditional CAM allocation and scoped review publication; not complete harness',
    'updated_utc':datetime.now(timezone.utc).isoformat(),'source_script_sha256':sha(Path(__file__)),
    'source_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),
    'checks':{n+'.json':sha(OUT/(n+'.json')) for n in names},'source_update_sha256':sha(OUT/'source_update.json'),
    'images':data['render_manifest']['images'],'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_REVIEW_PUBLISHED_MAIN_UNCHANGED')
