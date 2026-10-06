"""Build local review/measurement documents from this study's actual evidence.
No main geometry, hardware files or manufacturing orders are changed.
"""
from pathlib import Path
import json,csv,hashlib,html,re,zipfile,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
def read(n):return json.loads((H/n).read_text())
def dump(n,x): (H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def link(p,label=None):return f'<a href="{p}">{html.escape(label or p)}</a>'
inv={r['id']:r for r in read('assembly_inventory.json')['objects']}
current_bom={r['id']:r for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text())}
for n,r in current_bom.items():
 inv.setdefault(n,{'properties':{}})['properties'].update(label_zh=r['name'])
coupons=read('jlc_coupons/manifest.json');mates=read('mated_connector_review.json');tools=read('fastener_access_review.json')
mass=read('pa12_mass_and_torque.json');inserts=read('insert_seat_screening.json')
classify=json.loads((ROOT/'mechanical/reports/manufacturing_classification.json').read_text())
current_ids=[n for n in current_bom if any(k in n for k in ['Screw','Nut','Insert','Washer']) and not n.startswith('Coupon')];toolmap={r['id']:r for r in tools}
for r in json.loads((ROOT/'mechanical/reports/prearrival_geometry.json').read_text())['servo_ears']:
 toolmap[r['id']+'_Screw']={'nominal_shank_length_mm':r['screw_length_mm'],'nominal_head_diameter_mm':3.5,'nominal_head_height_mm':1.4}

# Every current fastener is represented, while hypothetical candidates stay separate.
cols=['part_id','kind','current_model_label','source_spec_if_present','quantity','model_shank_length_mm_approx','model_head_diameter_mm_approx','model_head_height_mm_approx','straight_tool_blockers_complete_assembly','handle_blockers_complete_assembly','purchase_release','note']
with (H/'fastener_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
 for n in current_ids:
  p=inv[n]['properties'];t=toolmap.get(n,{})
  w.writerow(dict(part_id=n,kind=next((k for k in ['Screw','Nut','Insert','Washer'] if k in n),'other'),current_model_label=p.get('label_zh'),source_spec_if_present=p.get('fastener_spec',''),quantity=1,model_shank_length_mm_approx=round(t.get('nominal_shank_length_mm',0),3) if t else '',model_head_diameter_mm_approx=round(t.get('nominal_head_diameter_mm',0),3) if t else '',model_head_height_mm_approx=round(t.get('nominal_head_height_mm',0),3) if t else '',straight_tool_blockers_complete_assembly='; '.join(x['part'] for x in t.get('shaft_blockers_in_complete_assembly',[])),handle_blockers_complete_assembly='; '.join(x['part'] for x in t.get('handle_blockers_in_complete_assembly',[])),purchase_release='BLOCKED',note='Current nominal CAD inventory, not a released purchase BOM. Geometry-derived sizes are approximate; source labels/selected manufacturer drawings take precedence.'))

measure=[];couponhtml=[]
descs={
'C01_M2_inserts':'M2 嵌件底孔：Ø3.0 / 3.1 / 3.2 / 3.3 / 3.4，深4。参考 FINE SL M2，外径3.6、长3；孔底留3。',
'C02_M3_inserts':'M3 嵌件底孔：Ø3.8 / 3.9 / 4.0 / 4.1 / 4.2，深5。参考 FINE SL M3，外径4.6、长4；孔底留3。',
'C03_small_bearings':'靠缺角的一排为俯仰轴承外径12配合孔：11.9 / 12.0 / 12.1 / 12.2；另一排为轮轴承外径13配合孔：12.9 / 13.0 / 13.1 / 13.2。',
'C04_yaw_bearing':'Yaw 轴承外径32配合孔：Ø31.9 / 32.1 / 32.3。',
'C05_yaw_journal':'Yaw 轴承内径20配合轴：Ø19.8 / 20.0 / 20.2；露出高8，底板3，总高11。',
'C06_screw_bearing':'M2 通孔Ø2.2 / 2.4，沉孔Ø4.2深1.6；M3通孔Ø3.2 / 3.4，沉孔Ø6.2深2.0 / 3.2。用于实测选定头型的承压与工具空间。',
'C07_M2_nut_pockets':'M2 螺母窝对边4.2 / 4.4 / 4.6，深1.8；中心通孔Ø2.2。参考 GB/T6170 M2 螺母对边4、高1.6。'}
for p in coupons['parts']:
 pid=p['id'];features=[]
 for i,q in enumerate(p['holes']):
  text=f"Ø{q['diameter']:g}";kind='bore';nom=q['diameter']
  if p.get('nut_pockets_AF_mm'):
   text='AF'+str(p['nut_pockets_AF_mm'][i]);kind='hex_AF';nom=p['nut_pockets_AF_mm'][i]
  features.append(dict(x=q['x'],y=q['y'],d=q['diameter'],label=text,kind=kind,nominal=nom,depth=q.get('depth','through'),counterbore=q.get('counterbore','')))
 if p.get('journal_diameters_mm'):
  features=[dict(x=(i-1)*29,y=0,d=d,label=f'Ø{d:g}',kind='journal_OD',nominal=d,depth=8,counterbore='') for i,d in enumerate(p['journal_diameters_mm'])]
 width,height,_=p['dimensions_mm'];scale=min(5,680/(width+10));vw=(width+10)*scale;vh=(height+19)*scale
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" role="img" aria-label="{pid}孔位图，毫米">',f'<rect x="{5*scale}" y="{5*scale}" width="{width*scale}" height="{height*scale}" fill="#e4ece8" stroke="#254e49" stroke-width="1.5"/>',f'<rect x="{5*scale}" y="{(height+3)*scale}" width="{2*scale}" height="{2*scale}" fill="white" stroke="#254e49"/>']
 for i,q in enumerate(features):
  x=(q['x']+width/2+5)*scale;y=(height/2-q['y']+5)*scale
  svg += [f'<circle cx="{x}" cy="{y}" r="{max(q["d"]/2*scale,2)}" fill="white" stroke="#254e49"/>',f'<text x="{x}" y="{y+q["d"]/2*scale+3.5*scale}" text-anchor="middle" font-family="sans-serif" font-size="{2.8*scale}">{i+1}: {q["label"]}</text>']
  measure.append(dict(coupon=pid,feature=i+1,kind=q['kind'],nominal_mm=q['nominal'],x_mm=q['x'],y_mm=q['y'],depth_or_length_mm=q['depth'],counterbore_nominal=str(q['counterbore']),actual_X_mm='',actual_Y_mm='',actual_depth_mm='',mating_part_MPN='',mating_part_actual_mm='',fit_observation='',insert_method_and_temperature='',installed_height_mm='',measured_test_load_N='',measured_test_torque_Nm='',crack_or_spin='',date='',batch_id='',operator=''))
 svg.append('</svg>');(H/'jlc_coupons'/f'{pid}.svg').write_text(''.join(svg))
 couponhtml.append(f'<article class="coupon"><h3>{pid}</h3><p>{descs[pid]}</p><img src="{pid}.svg" alt="{pid} 尺寸索引"><p class="small">外形 {" × ".join(str(x) for x in p["dimensions_mm"])} mm · {p["volume_cm3"]:.2f} cm³ · 实体/网格检查 {p["status"]}</p>{link(pid+".stl","下载 STL")}</article>')
with (H/'jlc_coupons/measurement_record.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(measure[0]));w.writeheader();w.writerows(measure)
readme='''# MORI · 嘉立创 PA12 局部配合试片

用途：在整机打印前校准实际打印批次、嵌件、轴承和螺钉的配合。只包含7件独立试片，不包含整机制造放行，也未代下单。

- 工艺建议：嘉立创 MJF PA12；原色、清粉、无喷漆。与后续承力件保持相同工艺/材料；打印方向由供应商排版控制，要求记录或保持接口方向可比。
- 单位：mm，STL按1:1导入，绝不自动缩放。各试片平底为方向基准；从有孔/凸轴的一面看，缺角在左下。编号按图示及 measurement_record.csv 坐标对应。
- 每个STL闭合、单一连通实体，已重新读取导出文件检查；这不证明真实孔径、配合力或强度。
- 先测量清粉后的孔径/对边/深度，再装金属件。记录厂家、批次、嵌件/轴承实际尺寸、装入力、旋转松紧、螺钉承压和拆装后的损伤。不得把“塞得进去”当强度合格。
- 嵌件试片孔位供比较，厂家名义底孔不自动成为最终打印孔。PA12为热塑性材料，安装温度与方法按实际嵌件及样件试验确定；树脂不要照搬热熔安装。
- 轴承试片只校准径向尺寸，不能替代肩部、轴向保持和实际关节载荷测试。压外圈时仅通过外圈施力，不把压入力穿过滚珠。
- 螺母试片检查是否装得进且不空转；不在试片内直接打印M2/M3螺纹。
- 本包不包含切片/G-code；嘉立创粉末打印由其设备和排版流程处理。不要套用桌面FDM的填充率参数。

'''+ '\n'.join('## '+k+'\n\n'+v+'\n' for k,v in descs.items())+'''
具体孔中心坐标见 manifest.json 和 measurement_record.csv；SVG为尺寸索引图，不按屏幕尺寸测量。

数据来源：
- 嘉立创设计指南：https://jlc3dp.com/help/article/3d-printing-design-guideline
- 嘉立创MJF：https://jlc3dp.com/3d-printing/multi-jet-fusion
- FINE嵌件图：https://www.finesz.com/shk.php
- GB823厂家尺寸表：https://www.wqjgj.cn/product/luoding/shizicao/2158.html

当前整机中的许多嵌件仍是旧试配占位。不能把本试片所列FINE型号直接装进旧模型的孔内；接口需要按选定型号完成设计变更后才可放行整机。
'''
(H/'jlc_coupons/README_先读.md').write_text(readme)

css='''*{box-sizing:border-box}body{margin:0;background:#f4f5f1;color:#1f302d;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1160px;margin:auto;padding:45px 30px 80px}h1{font-size:38px;line-height:1.2;letter-spacing:-1px;margin:10px 0 20px}h2{margin-top:50px;padding-top:20px;border-top:1px solid #ced9d1}h3{margin:8px 0}.eyebrow,.small{font-size:13px;color:#526960}.tag{font-size:12px;background:#deeae2;border-radius:20px;padding:5px 10px;display:inline-block}.notice{background:#fff0d9;border-left:4px solid #b26b24;padding:16px 20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card,.coupon{background:white;padding:22px;border:1px solid #dde3dc;border-radius:12px}img{display:block;max-width:100%;height:auto;border-radius:7px}a{color:#136654;text-decoration-thickness:1px;text-underline-offset:3px}table{border-collapse:collapse;width:100%;font-size:14px;background:white}td,th{text-align:left;vertical-align:top;padding:12px 14px;border-bottom:1px solid #dce3dc}th{background:#e4ece6}.scroll{overflow-x:auto}.metrics{display:flex;gap:20px;flex-wrap:wrap}.metric{background:white;border-radius:9px;padding:18px 22px;min-width:175px}.metric b{font-size:30px;display:block}.files{display:flex;gap:15px;flex-wrap:wrap}.muted{color:#61756d}code{overflow-wrap:anywhere;font-size:12px}@media(max-width:700px){main{padding:25px 16px}.grid{grid-template-columns:1fr}h1{font-size:29px}}@media print{body{background:white}main{padding:0}article,figure,tr{break-inside:avoid}h2{break-after:avoid}a{color:#1f302d}}'''
def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'</style><main>'+body+'</main></html>'
(H/'jlc_coupons/index.html').write_text(page('MORI PA12 配合试片','<p class="eyebrow">MORI / PRE-ARRIVAL / FIT COUPONS</p><h1>7 件局部配合试片</h1><p>先校准打印批次与金属件配合，再定整机孔径。尺寸均为毫米。</p><p class="notice">局部试片候选，尚未下单。当前整机仍有设计待确认项，不能由试片网格 PASS 推导整机可制造。</p><p class="files">'+link('measurement_record.csv','下载测量记录表')+link('manifest.json','尺寸与STL哈希')+link('README_先读.md','打印/测量说明')+'</p><div class="grid">'+''.join(couponhtml)+'</div>'))

assembly='''# MORI · 打样前装配与工具顺序

基线V1.2-M1.38，当前已应用M1.39。本文把73枚螺钉的工具包络筛查和29个对插壳体的结果整理为作业顺序。并非已完成真实试装。`fastener_inventory.csv`包含129个紧固件对象，73螺钉、20螺母、34嵌件、2垫圈；不把库内螺钉网格当作采购型号。

## 顺序与拆卸前置条件

1. 单件清粉、查孔、测关键厚度；先完成C01—C07配合试片。按最终嵌件或螺母方案安装紧固接口，不能直接热压当前模型中的通用嵌件占位。
2. 电源板、运动载板、IMU、9V与6V模块在开放的Load_Frame上安装。IMU及降压板从底面操作，先于电池托盘和轮驱总成。集成进电源板的是两路5V，9V/6V两个独立模块仍保留。
3. 后接口板先在可翻转的后壳上固定，并预接J3线束。其PHR-4保守包络与WeAct有0.0184mm³微小相交；需要核实际插头及模块堆叠，不视为已排除干涉。先插线可改善插拔顺序，不能消除静态碰撞。
4. 开放顶面安装运动载板与WeAct；选定排母前，不锁定模块最终高度。Motion J8在肚子上壳合上前插接。
5. 电源 J10、J12、J2、J3、J4、J5应在固定Yaw_Base承重桥装入前接好；J10还需在反力连接件装入前接好。插头12mm直线路径筛查见mated_connector_review.json，电线转弯、手指及卡扣工具尚未包含。
6. 固定承重桥插入Load_Frame，用左右横向M3锁紧，左右车轮保持拆下，以便侧向工具进入。电池托盘可以保留，但先开箱确认所需驱动头型。
7. 轮驱S288、定制金属输出件、686轴承与共用底盖组成轮驱模块。S288的12枚输出螺钉为厂家兼容M2自攻要求，不能替换成普通M2机牙。底盖4枚M3×25及2枚轮端M3×8仍按金属轴图和沉孔配合核定。
8. 头部固定/旋转轴承、反力连接、舵盘及两个SCS0009形成完整传动后，再安装俯仰头托。当前左俯仰短轴到舵盘有约2.2mm空隙，轴向保持和匹配舵盘未闭合；本步骤目前BLOCKED。新舵机耳座穿栓方案只解决耳座固定，不代表已解决传动。
9. CAM板、LCD框和相机在头托开放时安装。LCD三枚M2×12的原厂柱有效螺纹深度到货测量；不能盲拧到底。相机由现有结构与可拆前壳捕获，不新增压盖。
10. 头前壳从两侧上方锁两枚M2×12，拼缝M2×16随后锁紧。舵机/轴承手转无卡阻后，才合头后壳。按已确认的−20°俯仰与±60°Yaw范围检查服务线环。
11. 电池放入托盘并用现有绑带/软垫固定；接线、留拉手与退出方向；最后合肚子外壳并装车轮。拆卸按相反依赖，不强拉板上插头或电池引线。

## 工具与螺钉规格

- 本次空间筛查用Ø3×30mm直杆和Ø16×25mm手柄包络。模型整装状态下有阻挡不必然是缺陷，须看是否可通过上述前置顺序避开；这也不证明实际驱动头、手指及操作力都可行。
- M2小盘头候选GB823（现行标准对应型号需随供应商确认），厂家参考头径最大3.5、高1.4；优先先核本体承压环及工具再选择实际长度。
- 新耳座候选：M2×6一枚、M2×25一枚、M2×14两枚，配4枚M2六角螺母。已应用M1.39主模型，取消原耳座4个嵌件。先在U托脱离机身时预装4枚螺母。
- M3轮驱底盖和轮端为圆柱内六角候选；横向承重桥是低圆头候选。不要混用高头螺钉。当前模型Frame/Shell的M3头型需与实际商品重新核对。
- FINE SL M2外径3.6、M3外径4.6只作为明确图纸的候选。多数旧M2座无法直接满足该型号要求的材料包边，必须先改接口。完整筛查见insert_seat_screening.json。
- 没有规定未验证的锁紧扭矩。装配扭矩、热熔工艺和拉拔/抗转门槛应通过实际选定紧固件与相同打印工艺试片确定；不能直接套用金属螺纹表。
'''
(H/'装配顺序与紧固件.md').write_text(assembly)

handoff='''# MORI · 机械给电路/采购的接口反馈

本地交接文件。IMU评估要求曾发送给“建立 MORI 硬件开发项目”，随后按用户最新决定撤回扩板。其他条目未作为电路改板指令发送；未联系供应商。基于硬件已发布P5R6，IMU仍为P5R4；硬件源码和components.json未修改。请以新交接版接收这些要求，不在机械模型中挪动原生焊盘掩盖问题。

## 已确认的用户要求

- 取消独立后置开关和原壳孔；当前原生SW1仍在收到的PCB数据中，电路任务需删除或发布新配置。整机断电与电机物理急停由电路任务确定并返回操作界面要求。机械不把软件停机等同物理断能。
- 保留小型3S候选71×55×20mm；采购前提供含保护板、热缩、出线、插头的最大包络及质量。六节18650不是当前装配方案。
- 喇叭沿用用户SP3040图纸，未标尺寸是已授权估算；不替换型号。

## IMU最终决定及其他待确定接口

IMU第三固定点方案详见imu_mount_proposal.json：板框20×16→20×21mm；新增后侧5mm条带。新局部孔位(2.5,17.5)、(17.5,17.5)、(10,2.5)，建议试孔Ø2.4；第三孔周围禁布铜/器件圆Ø6.6。所有原器件与原孔在新坐标中一起Y+5，保证它们在机器人中的物理位置不变。第三轴世界坐标(-25,-50.5,108.4)。用户已撤回该扩板方案：保留原20×16mm及现有两个固定孔，不增加短座、螺钉或嵌件。以上20×21及第三孔尺寸仅存作历史提案，不得用于改板。

WeAct排母：模块官方是STM32F4 64Pin V1.1/F412RET6，不能混用F4x1 BlackPill。原生孔阵列2.54mm，A/B为2组2×12，C/D为2组2×3，E为1组2×4，E组安装侧及实际配置需核实。原生孔Ø1.0。现在6mm堆叠仅是假设；机械对核心板整体上移做了6–11mm、步长0.5mm的11个名义高度筛查，均未出现>0.02mm³静态干涉。该结果不包括排母实体、接触插深、退针防松或插拔行程，不能把11mm直接定为最终堆叠。请提供一套匹配公母件的精确MPN及装配剖面，再整体验证。

后接口板J3：PHR-4尺寸包络与MCU_Motion相交0.0184mm³。要求详细匹配塑壳和接触位姿复核；不直接移动原生连接器。当前原始位置见mated_connector_review.json，建议先预接后接口板，再安装运动载板。若改变WeAct堆叠，这一对必须重查。

## 仍需硬件给出的确定接口

1. 充电/PD具体方案、外壳Type-C插入到位基准与实际插头外壳、允许插拔力；当前USB开口不代表任意粗插头都能插到底。
2. 保险座、保险丝、耗能器件的真实外形、温升/散热/禁靠边界以及更换路径。不能仅用电阻额定功率定塑料安全距离。
3. 完整线束连接表：每端MPN、位号、针号、线径/绝缘外径、分支、屏蔽、线长和弯曲半径。PH/XH已建配对壳体，29处结果见mated_connector_review.json；XT30为保守满长度包络，不含真实插合深度。
4. CAM/OV3660连接器和FPC的准确版本、触点面、允许折弯区/弯曲半径；相机照片估算尺寸保留ASSUMED。
5. 两路5V已在电源板上，不再采购独立5V降压板。现有9V Pololu D36V50F9和6V D24V22F6仍是当前硬件方案的独立模块，不应一并删掉。

## SCS0009舵盘/轴采购需回复的数据

- 必须明确匹配SCS0009的20T/OD3.95输出；同样叫20T的SCS009资料存在4.8mm版本，不能互换。当前官方网页引言与规格表也有型号/齿数混杂，以确认的具体版本图纸为准。
- 提供舵盘外径/厚度、花键嵌入深度、安装面到舵机输出面的轴向距离、中心M2锁紧螺钉有效啮合、外圈孔距与孔径、材料和随附螺钉。已有SCS0009 A/0厂图的配件页标No Accessories，没有完成这些接口的尺寸。
- 当前左俯仰短轴X[-46,-38.9]，轴承X[-41,-37]，舵盘X[-36.7,-35.7]（mm）。短轴仅覆盖轴承宽度2.1/4mm，距舵盘2.2mm，且无闭合的轴向保持。这是未完成的传动设计，不是单纯待实测。
- 在匹配舵盘数据出来前，不能用打印20T小花键或放大舵盘占位来宣称传动完成。可先确定供应配置，随后设计完整金属短轴/保持与舵盘的连接；输出轴和双侧承重轴承的角色保持分离。

## 引用

- TDK AN-000393 v1.5 §3.1/3.2，三点固定是建议而非本项目硬性认证条款：https://invensense.tdk.com/wp-content/uploads/2024/04/AN-000393-TDK-InvenSense-IMU-PCB-Design-and-MEMS-Assembly-Guidelines-v1.5.pdf
- WeAct原厂：https://github.com/WeActStudio/WeActStudio.STM32F4_64Pin_CoreBoard
- FEETECH SCS0009：https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html

所有名义碰撞检查仅筛查建模几何；采购、PCB生产、整机打印和上电均未由本文件放行。
'''
(H/'电路与采购接口交接.md').write_text(handoff)

print_groups=[
('Load_Frame / Drive_Bridge / Motor_Retainer','承重托板与轮驱壳','PA12尼龙','承力板面作为测量基准；轴承孔轴和盖合平面不喷漆','轴承挡边约0.75mm处、嵌件孔与盖合面要局部复核；不能用平均壁厚放行'),
('Yaw_Base / Yaw_Reaction_Link / Pitch_Yoke','固定桥、反力件、Yaw/俯仰U托','PA12尼龙','配合孔与平面要求记录成形方向；槽内彻底清粉','舵盘传动尚未闭合；耳座穿栓已应用M1.39'),
('Pitch_Cradle / Display_Frame','俯仰头托与光学框','PA12尼龙','优先保护薄壁与相机夹持唇；倾斜摆放由工厂评估','CAM背座局部薄壁与相机尾槽薄边须分项处理；不等同整板厚度不足'),
('Battery_Tray','可拆电池托盘','PA12尼龙','托盘底面与两侧滑动面无涂装','实测电池/绑带/软垫和抽出力'),
('Wheel_Hub_L / Wheel_Hub_R','左右轮毂','PA12尼龙','轮轴孔和双D驱动面不得用喷漆改变尺寸','打印后核同轴度、轮胎配合和轴端夹紧；当前实心模型不自动套FDM低填充'),
('Head_Front / Head_Rear / Body_Upper / Body_Lower','四片外壳','首轮全部PA12（用户已确认）','先验证结构；暖白喷涂与黑色边圈放到装配确认后','若改树脂，壳内热熔嵌件方案须改为兼容连接；不能直接沿用热塑性工艺')]
printmd='''# MORI · 嘉立创打样建议（未下单）

建议第一轮用MJF PA12尼龙完成结构验证；承力件及壳体统一材料可避免同一轮同时调整热熔/胶粘两套接口。用户已确认首轮全部PA12，先验证结构。外壳要求暖白色时，后处理喷涂需另行确认；不能把尼龙原色说成白色。细致外观用白色树脂可作为后续方案，但不适合直接照搬热熔嵌件。

嘉立创官方指南给出的尺寸和壁厚是可制造性参考，不是关节强度保证。网站MJF页面列名义精度±0.3mm或0.4%；实际规则、零件大小、方向和订单工艺以报价审查为准。小孔的批次收缩必须通过试片测量，不能对整个采购件或机器人统一缩放。

推荐先提交7个局部试片核价，再处理主模型当前接口阻碍。本文不含自动上传、报价、制造放行或购买行为。

| 零件 | 材料建议 | 打印/后处理重点 | 未闭合项 |
|---|---|---|---|
'''+''.join(f'| {a} | {c} | {d} | {e} |\n' for a,b,c,d,e in print_groups)+'''

## 螺纹与安装服务

嘉立创当前公开嵌件服务列M3/M4/M5，不包含M2，并给出最小壁厚/工具平面要求。当前机器人有大量M2，不能假设平台会全部代装；需按试片结果自装或向供应商确认专门工艺。M2/M3不采用直接打印螺纹。

FINE SL嵌件候选M2外径3.6、底孔3.2、建议最小壁1.3；M3外径4.6、底孔4.0、建议最小壁1.6。现有主模型的多数嵌件是小尺寸通用占位，不能直接换采购件而不改座。4处舵机耳座已按用户批准改为穿栓螺母；其余嵌件座仍需逐处定型。

## 质量和驱动粗算

M1.38基线以15个本体打印件完整实心体积×1.01g/cm³计，打印件约748g，整机约1.30kg。密度来自Ricoh MJF PA12资料，非嘉立创实际批次测量；现有采购件质量仍含假设，线束、完整对插件和涂装尚未完整计入，不能据此承诺最终重量。

俯仰静态重力力矩最大约0.0059N·m；加10rad/s²角加速度，名义约0.00875N·m。“质量增加35%并额外加入0.01N·m摩擦”的假设场景约0.0218N·m。厂图SCS0009额定0.75kgf·cm，当前官网表0.7kgf·cm，保守比较取后者≈0.0686N·m；需核采购版本。该比较未覆盖线束反力、动态平衡、碰撞、齿隙和连续热负荷，不构成驱动或寿命合格判定。

## 检查结论的边界

- 7个试片：闭合实体、单一连通、STL回读拓扑PASS。尚未打印和测量。
- 15个本体打印件：完成有限法向射线壁厚筛查，不是每处全局最小壁厚证明；薄轴承挡边、盲孔顶盖与局部薄片需按具体功能处理。
- 29个插头外壳：28个保守包络无静态相交，1个待详细复核。包含装入前置条件，不含全部线缆。
- M1.39已应用耳座穿栓螺母、连续相机扩口及PA12材料。IMU扩板已撤回，仍是原20×16mm两孔。

来源：
- https://jlc3dp.com/3d-printing/multi-jet-fusion
- https://jlc3dp.com/help/article/3d-printing-design-guideline
- https://jlc3dp.com/help/article/threaded-insert-service
- https://www.finesz.com/shk.php
- https://3d.ricoh.com/wp-content/uploads/2019/10/Ricoh-TDS-MJF-PA12-Web-Final.pdf
'''
(H/'嘉立创打样建议.md').write_text(printmd)

# Persist a precise work ledger: checked candidates are not installed designs.
work={
'coupon_design':{'status':coupons['status'],'scope':'7 independent calibration coupons: closed one-piece mesh and STL roundtrip','evidence':'jlc_coupons/manifest.json','physical_validation':'NOT_TESTED'},
'servo_ear_candidate':{'status':read('servo_candidate_motion.json')['status'],'scope':'4 nut conversions,130 poses,nominal nut entry','evidence':'../../reports/prearrival_validation.json','adoption':'USER_APPROVED_M1.39','applied_to_main':True},
'camera_aperture_candidate':{'status':read('camera_aperture_candidate.json')['status'],'scope':'775 assumed-FOV rays, one continuous aperture, no added overlaps','evidence':'../../reports/prearrival_validation.json','adoption':'USER_APPROVED_M1.39','applied_to_main':True},
'imu_third_mount_proposal':{'status':'NOT_APPLICABLE','scope':'20x21 proposal spatial check; original PCB remains intact','evidence':'imu_mount_proposal.json','adoption':'WITHDRAWN_BY_USER_KEEP_ORIGINAL_TWO_HOLES'},
'mated_connectors':{'status':'BLOCKED','scope':'29 housings checked, rearJ3 conservative overlap requires exact interface; wire bends missing','evidence':'mated_connector_review.json'},
'weact_stack_screening':{'status':'PASS','scope':'11 static rigid core heights6..11mm; actual sockets and pin engagement unresolved','evidence':'weact_stack_review.json','selected_interface':'BLOCKED'},
'fastener_inventory':{'status':'PASS','scope':'129 existing objects listed,73 tool approaches screened; not final supplier BOM','evidence':'fastener_inventory.csv','seat_and_procurement_release':'BLOCKED'},
'insert_compatibility':{'status':'BLOCKED','scope':'Several old seats do not fit selected-candidate reference wall/depth; no automatic enlargement','evidence':'insert_seat_screening.json'},
'mass_and_torque_scenarios':{'status':'PASS','scope':'Recomputed PA12 full-solid estimate with explicit unmeasured inputs; no strength/dynamics claim','evidence':'pa12_mass_and_torque.json','physical_validation':'NOT_TESTED'},
'lcd_conversion_diagnosis':{'status':'BLOCKED','scope':'SourceBRep valid;107/108 mesh stillnonmanifold after investigated settings; original mesh/source retained','evidence':'lcd_tessellation_diagnosis.json'},
'lcd_conservative_separation':{'status':read('lcd_connector_bounds_review.json')['status'],'scope':'Full CAD bounds of107/108 separate from other parts at130 nominal poses; gap search capped5mm, no mesh alteration','evidence':'lcd_connector_bounds_review.json','exact_mesh_repair':'BLOCKED'},
'head_transmission':{'status':'BLOCKED','scope':'Left trunnion-to-horn gap2.2mm, incomplete bearing engagement and axial retention; matching horn missing','evidence':'电路与采购接口交接.md'},
'harness_routes':{'status':'NOT_TESTED','scope':'Rigid mating housings complete in scope; finite service-loop and bend design waits mounting and connector decisions; no speculative holes','evidence':'电路与采购接口交接.md'},
'electrical_handoff':{'status':'PASS','scope':'IMU expansion assessment sent then withdrawn by user; native boards unchanged','evidence':'电路与采购接口交接.md','hardware_response':'NO_IMU_EXPANSION_REQUIRED'},
'jlc_material_and_production':{'status':'BLOCKED','scope':'PA12 confirmed and coupon package prepared; whole-robot design not released','evidence':'嘉立创打样建议.md'}}
dump('progress.json',{'baseline':'V1.2-M1.38','scope':'Pre-arrival studies based onM1.38; ear nuts/camera/PA12 applied inM1.39; IMU expansion withdrawn','fabricator':'JLC3DP recommendation only, no upload/order','work_packages':work,'hardware_files_read_only':True,'whole_robot_manufacturing_release':'BLOCKED'})
sources=[]
for fn in ['sources/downloads.json','sources/additional_sources.json']:
 for r in read(fn):
  if isinstance(r,dict):sources.append(r)
files=[]
for p in sorted((H/'sources').iterdir()):
 if p.is_file():files.append({'file':str(p.relative_to(H)),'sha256':sha(p),'bytes':p.stat().st_size})
dump('source_manifest.json',{'retrieved_sources':sources,'downloaded_file_hashes':files,'received_hardware_contract_sha256':sha(ROOT/'contracts/components.json'),'main_blend_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),'limitations':'Evidence cache only. MPN/revision, physical measurements, availability and price are separate requirements.'})

matrows=[]
for r in mates['rows']:
 dep=sorted({a['target'] for a in r['straight_path_12mm_candidates']})
 matrows.append([html.escape(r['board']+'/'+r['ref']),html.escape(r['mating']),r['static_status'],'；'.join(html.escape(a['target']) for a in r['overlap_candidates']) or '未检出包络重叠','、'.join(map(html.escape,dep)) or '当前包络未检出阻挡'])
thinrows=[]
for r in inserts:
 h=r['host_screening']
 if h and not r['sampled_radial_wall_meets_reference']:thinrows.append([r['id'],h['part'],f"{h['minimum_remaining_wall_for_proposed_OD_mm']:.2f}",r['supplier_min_wall_mm']])
body='''<p class="eyebrow">MORI / V1.2-M1.39 / PRE-ARRIVAL REVIEW</p><h1>打样前，先把接口做完整。</h1><p>嘉立创材料与试片建议、实际几何筛查，以及需要确认的局部方案。主模型已更新M1.39：穿栓螺母和椭圆扩口已应用，材料全PA12；IMU保留原两孔。</p><p class="notice"><b>整机制造放行：BLOCKED。</b>已完成的分析与试片设计不等于整机接口已完成。头部传动、部分嵌件座、真实排母/插头与电路断能接口仍需闭合。</p>'''
body+='<div class="metrics"><div class="metric"><b>7</b>闭合配合试片</div><div class="metric"><b>29</b>对插壳体筛查</div><div class="metric"><b>73</b>螺钉工具路径</div><div class="metric"><b>≈1.30 kg</b>PA12假设整机质量</div></div>'
body+='<h2>已采用的局部方案</h2><div class="grid"><article class="card"><span class="tag">已应用 M1.39</span><h3>舵机耳座：穿栓＋螺母</h3><p>保持孔位与外轮廓，4处嵌件换4枚螺母；3处内沉槽，前柱用贯穿长螺钉。没有新增打印件。130姿态及螺母12mm入槽路径检查通过，强度待试打。</p><img src="servo_nuts_back.png" alt="舵机耳座穿栓候选"><p>'+link('servo_mount_candidate.blend','Blender候选')+' · '+link('servo_candidate_motion.json','检查结果')+'</p></article><article class="card"><span class="tag">已应用 M1.39</span><h3>相机壳孔：连续椭圆扩口</h3><p>镜头与捕获结构不动，删除旧孔叠加轮廓。775条名义视线无遮挡；不切黑色边圈。照片估算与实际镜头视角仍待校准。</p><img src="camera_aperture_candidate.png" alt="连续椭圆相机孔候选"><p>'+link('camera_aperture_candidate.blend','Blender候选')+' · '+link('camera_aperture_baseline.png','修改前')+' · '+link('camera_aperture_candidate.json','检查结果')+'</p></article></div>'
body+='<article class="card"><h3>IMU保留原两孔；第三固定点提案已撤回</h3><p>在原20×16mm板后方增加5mm，元件及两个原孔实际位置不动。第三孔与Load_Frame一体短座配合，新增1枚螺钉和1个嵌件。空间检查通过；用户已撤回此提案，保留20×16mm及两个原孔；以上扩板数据仅作历史记录。</p>'+link('imu_mount_proposal.json','孔位与坐标')+'</article>'
body+='<h2>嘉立创材料与试片</h2><p>首轮建议PA12尼龙做结构验证，喷涂放到装配确认之后。当前大量M2连接不能假设嘉立创会代装嵌件；其公开服务仅列M3/M4/M5。材料偏好仍待答复。</p>'+table(['零件','用途','材料建议','制造重点'],[[a,b,c,d] for a,b,c,d,e in print_groups])
body+='<p class="files">'+link('jlc_coupons/index.html','7件试片 · 孔位图和测量表')+link('MORI_PA12_fit_coupons.zip','下载试片包')+link('嘉立创打样建议.md','完整材料与打印说明')+'</p><img src="jlc_coupons/overview.png" alt="7件试片总览">'
body+='<h2>对插与装配顺序</h2><p>28个壳体保守包络无静态重叠；后板J3与WeAct存在0.0184mm³包络重叠，需细化。右列列的是完整装配状态下12mm直线路径的阻挡物，可通过先插接再合装解决部分阻挡。没有宣称线束、手指或锁扣已全部验证。</p>'+table(['接口','配对件','静态状态','静态候选重叠','插接前需保持拆下'],matrows)
body+='<p class="files">'+link('mated_connector_review.blend','独立插头检查模型')+link('装配顺序与紧固件.md','装配顺序与工具')+link('fastener_inventory.csv','129件当前紧固件清单')+'</p>'
body+='<h2>没有被几何 PASS 覆盖的问题</h2><div class="grid"><article class="card"><h3>头部传动未闭合</h3><p>左俯仰短轴仅进入4mm宽轴承约2.1mm，到占位舵盘仍有2.2mm间隔。匹配20T/Ø3.95舵盘、连接与轴向保持需完成。新耳座候选不解决这个传动缺口。</p></article><article class="card"><h3>旧嵌件占位不能直接采购</h3><p>多数旧M2座不足以直接接纳所查FINE型号的外径和推荐包边。应确定实际连接方法并修改相应座，不能把通用占位标成最终尺寸。</p></article><article class="card"><h3>线束与电路接口</h3><p>原SW1删除、物理断能方式、充电/PD、保险座和耗能器件需电路交接；完整弯曲与服务环没有验证，未新增预估走线孔。</p></article><article class="card"><h3>LCD原厂连接器网格</h3><p>107/108两个连接器的原始CAD实体有效，但网格转换仍有缺陷；原厂形状未被删除或缩放，完整外接框在130个名义姿态中均未碰到其他零件（间隙搜索上限5mm）。这关闭了该包络的名义避让检查，未修复网格，也未验证插头与实物公差。</p></article></div>'
body+='<details><summary>查看FINE候选嵌件包边不足的筛查位置</summary><p>有限射线筛查；单位mm。负数表示候选外径可能超出已有材料。此表不是已选采购件的强度判定，也不表示允许自动改外轮廓。</p>'+table(['旧对象','宿主','候选外径后的最小采样包边','厂家建议'],thinrows)+'</details>'
body+='<h2>计算、来源与交接文件</h2><p>M1.38基线的PA12实心质量约748g，含现有硬件假设的整机约1.30kg，尚未完整计入线束、插头和涂装。俯仰10rad/s²名义需求约0.00875N·m；假设加重35%和额外0.01N·m摩擦时约0.0218N·m。它们是设计场景，不能当作实测或动态平衡/连续热能力验证。</p><p class="files">'+''.join(link(p,l) for p,l in [('pa12_mass_and_torque.json','质量与力矩明细'),('weact_stack_review.json','WeAct堆叠筛查'),('lcd_connector_bounds_review.json','LCD连接器保守避让'),('电路与采购接口交接.md','电路/采购交接'),('progress.json','工作状态'),('source_manifest.json','来源与哈希')])+'</p><p class="small">本页由 package_review.py 从实际检查报告生成。无采购订单、无文件上传、无硬件源码修改。所有打印件仍需实物校准与验证。</p>'
(H/'index.html').write_text(page('MORI · 打样前接口检查',body.replace('Blender候选','批准时的候选Blender').replace('耳座穿栓候选','耳座穿栓方案')))

with zipfile.ZipFile(H/'MORI_PA12_fit_coupons.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted((H/'jlc_coupons').iterdir()):
  if p.suffix in ['.stl','.svg','.json','.csv','.md','.html'] or p.name=='overview.png':z.write(p,'MORI_PA12_fit_coupons/'+p.name)
dump('package_manifest.json',{'baseline':'V1.2-M1.38','current_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),'hardware_contract_sha256':sha(ROOT/'contracts/components.json'),'coupon_zip_sha256':sha(H/'MORI_PA12_fit_coupons.zip'),'coupon_stl_count':len(coupons['parts']),'main_geometry_changed':True,'current_revision':'V1.2-M1.39','manufacturing_release':'BLOCKED','orders_placed':0,'files_uploaded':0})
print('REVIEW_PACKAGE_COMPLETE',len(measure),'coupon features;',len(current_ids),'fasteners;',len(mates['rows']),'mated connectors')
