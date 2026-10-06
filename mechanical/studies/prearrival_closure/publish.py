"""Publish source-backed prearrival review. Does not rebuild or edit CAD."""
from pathlib import Path
import json, hashlib, html, csv, collections
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(name):return json.loads((HERE/name).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
eng=read('engineering.json');asm=read('assembly_preflight.json');paths=read('rigid_assembly_paths.json')
routes=read('harness_routes.json');neck=read('head_route_space.json');seq=read('sequence_dependencies.json')
dual=read('dual_body_sequence.json')
receipt=read('p5r7_fit.json');follow=read('p5r7_receipt/followthrough.json')
dual7=read('p5r7_receipt/dual_body_sequence.json');service7=read('p5r7_receipt/service.json')
a1_path=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_E_pin_fit_A1.json'
a1=json.loads(a1_path.read_text())
assert a1['base_handoff_sha256']==receipt['handoff_sha256']
animation=read('body_sequence_animation.json')
full_animation=json.loads((ROOT/'mechanical/animation/manifest.json').read_text())
full_animation_updated=bool(full_animation.get('rendered_video') and full_animation.get('body_sequence_readback',{}).get('status')=='PASS')
replay=read('p5r7_receipt/route_replay.json')
assert replay['base_report_sha256']==digest(HERE/'harness_routes.json')
assert receipt['handoff_sha256']==follow['handoff_sha256']
assert follow['candidate_sha256']==dual7['candidate_sha256']
current_source=digest(ROOT/'mechanical/mori_v1_2.blend')
source=eng['source_blend_sha256']
if current_source!=source:
    cfg=json.loads((ROOT/'config/geometry.json').read_text())
    baseline=ROOT/cfg['head_axial_retention']['baseline_blend']
    assert digest(baseline)==source
assert all(d['source_blend_sha256']==source for d in [eng,asm,paths,routes,neck,seq,dual])
font=FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc')
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':12})
fig,axes=plt.subplots(1,2,figsize=(12.4,4.7),constrained_layout=True)
ax=axes[0]
parts=sorted((r for r in eng['entries'] if r['category']=='PRINTABLE'),key=lambda r:-r['mass_g'])[:6]
labels={'Body_Upper':'身体上壳','Body_Lower':'身体下壳','Wheel_Hub_L':'左轮毂','Wheel_Hub_R':'右轮毂','Load_Frame':'主托架','Yaw_Base':'承重桥','Head_Rear':'头后壳','Pitch_Yoke':'俯仰 U 托'}
ax.barh([labels.get(r['id'],r['id']) for r in parts],[r['mass_g'] for r in parts],color='#46746e')
ax.invert_yaxis();ax.set_xlabel('模型实体质量估算 / g');ax.set_title('主要 PA12 件（未测量）',loc='left',weight='bold')
for i,r in enumerate(parts):ax.text(r['mass_g']+1,i,f"{r['mass_g']:.1f}",va='center')
ax.set_xlim(0,max(r['mass_g'] for r in parts)*1.18);ax.spines[['top','right']].set_visible(False)
ax=axes[1]
for axis,label,color in [('pitch','俯仰','#2e756d'),('yaw','水平转向','#c08032')]:
    rows=[r for r in eng['head_scenarios'] if r['axis']==axis]
    ax.plot([r['acceleration_rad_s2'] for r in rows],[r['stress_scenario_Nm'] for r in rows],'-o',label=label,color=color)
ax.axhline(eng['head_scenarios'][0]['rated_reference_Nm'],color='#6d7380',linestyle='--',label='SCS0009 4.8V 表列参考')
ax.set_xlabel('头部角加速度假设 / rad/s²');ax.set_ylabel('转矩 / N·m');ax.set_title('带附加假设的转矩筛查',loc='left',weight='bold')
ax.legend(fontsize=9,frameon=False);ax.set_ylim(0,.074);ax.spines[['top','right']].set_visible(False)
fig.suptitle('M1.43 到货前工程计算 · 不含未选部件，不代表强度或连续工况验证',fontsize=13)
fig.savefig(HERE/'engineering_overview.png',dpi=160);plt.close(fig)

# Every rendered actor receives an operation or an explicit hold. Factory
# sub-objects do not become extra procurement / assembly items.
bom={r['id']:r for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text())}
fast={r['id']:r for r in asm['fasteners']};ins={r['id']:r for r in asm['insert_installation']}
def operation(n):
    if n in ins:return 'S00','裸打印件先装嵌件；工具包络已检查，试片工艺待验证'
    if n in fast:return 'FASTENER',fast[n].get('stage',fast[n].get('reason',''))
    if n.startswith(('Yaw_Horn','Pitch_Horn','Pitch_Trunnion','Yaw_Reaction_','Pitch_Bearing','Yaw_Bearing')):return 'HOLD_HEAD','舵盘/短轴/反力连接及轴向叠层等厂家资料；轴承型号接口仍待锁定'
    if n.startswith(('Drive_Motor','S288_Output','Wheel_Axle','Wheel_Bearing','Wheel_Spacer_L_0','Wheel_Spacer_R_0','Motor_Top_Pad')):return 'S01','轮驱电机与法兰轴/轴承台面预装；原配输出盘不拆成额外采购件'
    if n.startswith(('Drive_Bridge','Motor_Retainer','Wheel_Cap_Clamp')):return 'S02','轮驱上下座包夹；装软垫、螺母和底盖'
    if n.startswith(('Drive_L_','Drive_R_')):return 'S05','由侧入口装四枚 DIN934 M2 螺母，再与主托架穿栓连接'
    if n=='Load_Frame' or n.startswith(('IMU_','Body_IMU','Wheel_Buck','Head_Buck')):return 'S03','主托架底面三块板在台面固定，后并入轮驱'
    if n.startswith(('Power_Module','Power_Board','MCU_Carrier','Carrier_')):return 'S04','主托架上方载板、电源板；桥前预插线'
    if n=='MCU_Motion':return 'HOLD_7','主模型仍为旧收到版；P5R7独立接收候选已校核，E直针/原厂STEP孔形冲突待核'
    if n.startswith(('Body_Upper','Speaker','Rear_Interface','USB_Receptacle','Power_Switch')):return 'S06','裸上壳先装喇叭与后接口板；保留取消开关的旧原生模型仅作历史收到版本'
    if n.startswith('Yaw_Base'):return 'S07–08','上壳暂抬14mm/倾15°，桥保持水平落座，锁紧后再合壳；407姿态候选已查'
    if n.startswith(('Pitch_Yoke','Pitch_Servo','Pitch_Output','Head_Pitch_','Yaw_Servo','Yaw_Output','Head_Yaw_')):return 'S09','离机双舵机座；先俯仰再水平舵机'
    if n.startswith(('Pitch_Cradle','CAM_','Onboard_MIC')):return 'S10','离机头托与 CAM 板；MEMS 是主板原配件'
    if n.startswith(('Display_','LCD_','Camera_','Face_Joint')):return 'S11','屏幕和相机先装到离机显示架，再与头托连接'
    if n.startswith(('Head_Front','Head_Rear','Head_Cradle','Head_Seam')):return 'S12','前壳捕获相机后上方锁紧，再合后壳；先完成线束'
    if n.startswith('Battery'):return 'S14','离机托盘软垫/绑带装电池后滑入；两侧锁紧，轮子仍未装'
    if n.startswith(('Body_Lower','Shell_')):return 'S15','接线与头部总成完成后封下壳'
    if n.startswith(('Wheel_Hub','Tire_','Wheel_Spacer','Wheel_End')):return 'S16','轮毂与轮胎、外隔套最后套轴并锁紧'
    return 'UNASSIGNED','需要人工归档，不能默认为已检查'
coverage=[]
for e in eng['entries']:
    n=e['id'];op,note=operation(n);b=bom[n]
    coverage.append(dict(id=n,name=b['name'],operation=op,note=note,category=b['category'],data_status=b['data_status'],mass_g=e['mass_g']))
assert len(coverage)==200 and not any(r['operation']=='UNASSIGNED' for r in coverage),[r for r in coverage if r['operation']=='UNASSIGNED']
with (HERE/'assembly_coverage.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
(HERE/'assembly_coverage.json').write_text(json.dumps(dict(source_blend_sha256=source,actors=coverage,status='PASS',scope='200 scene actors assigned to operations/holds; not 200 independently purchased parts and not complete assembly qualification'),ensure_ascii=False,indent=2)+'\n')

process='''# M1.43 到货前装配工艺复核

本版是 **PROTOTYPE / UNVALIDATED**。本页26组检查使用 M1.43 与 P5R6（IMU 为 P5R4）。P5R7 已在本轮后半段正式交接，另行接收为独立候选，旧板结果不能直接称为新板通过。主模型没有改动。刚体路径、工具包络、手工工艺和线束是四个独立检查范围。

## 已有证据

- 新增 26 组刚体装入路径、2,087 个离散位置；每组结果同时列出移动件、已装件和先决条件。
- 69 处现有紧固件的分阶段工具空间通过；4 处头部传动相关紧固件仍等厂家资料。
- 34 处嵌件检查了裸打印件上的工具包络；温度、压入力、配合孔及背面支撑仍需 PA12 试片。不能在装好 PCB 后热装嵌件。
- 旧P5R6的29处对插外壳中，28处通过、J3冲突；P5R7独立候选重新检查29处均通过。各自检查均包括全装静态位置及规定台面阶段12 mm / 0.5 mm插拔抽样。没有包含手指和线材弯曲。
- 200 个现有场景对象已逐项归入工序或明确的暂停点。原厂零件的拆分显示对象不计作额外采购件。

## 工序与先决条件

| 工序 | 操作 | 检查与限制 |
|---|---|---|
| S00 | 15 件整机 PA12 打印件清理、标识；分件装 34 个嵌件 | 先做配合试片；嵌件规格按既有 FINE 清单，工具必须满足已查包络。托架及试片另列。 |
| S01 | 两只 S288 在台面装金属法兰轴，再依次装内 686ZZ、4.5 mm 金属隔套、外 686ZZ | 输出六孔螺钉工具先于轴承；自攻螺钉与原厂孔、压装力仍须确认。不要把金属轴/隔套当打印件。 |
| S02 | 电机/轴承组件由下方进入敞开的 Drive_Bridge；装软垫、捕获螺母与共用底盖 | 底盖关闭前核对轴承座完整贴合；不靠电机输出轴承承受全部轮载。 |
| S03 | 倒置裸 Load_Frame，安装 IMU、9 V 和 6 V 降压板 | IMU 仍为原 20×16 mm 两孔。9 V/6 V 板仍外置；双 5 V 已集成在电源板上。 |
| S04 | 翻正主托架，安装电源 PCB 与运动载板，插线预装 | 先锁载板螺钉再插核心板。P5R7候选元件面朝上、针向下，板间距11.04 mm；核心板+E向上抽出30 mm路径通过。E针脚/原厂STEP孔径冲突未解除，不能按候选下单。 |
| S05 | 已装板的主托架自上方与轮驱结合；四枚 M2×8 锁紧 | 先经侧入口放入 DIN934 M2 螺母。螺母对边/厚度须匹配选定槽。 |
| S06 | 离机身体上壳安装 SP3040、垫片、后接口 PCB，预接其插头 | 喇叭固定在壳上。扬声器线两端均为功放输出，不能将其中一端当机壳地。P5R7 后板已交接，候选集成另行复核。 |
| S07–08 | 上壳倾斜托住，承重桥保持水平单独落座并锁紧，再合上壳 | 下文列出通过的407个组合位置及工具路径；需分别支承两个部件，不能把两者绑成一个刚体移动。 |
| S09 | 在台面组装 Pitch_Yoke：先俯仰，再水平舵机 | 俯仰舵机先在 X+30 mm 处从上方下放，再向左平移 30 mm；不能从另一侧墙穿入。上下耳使用 1.5 mm 短柄内六角工具，已查连续转角 240°/168°。 |
| S10 | 离机头托安装 CAM；结合双舵机座及承重轴承/短轴 | CAM 32.6 mm 孔网格不变。**舵盘、短轴及相关轴向锁紧在此暂停，等厂家资料定型。** |
| S11 | 原厂 LCD 装入离机 Display_Frame，相机进入原夹持口；光学组件从前方与头托连接 | LCD 顺 10° 光轴方向装入；先接 FFC/FPC，再合头壳。相机卡位基于照片估算，需实物校准。 |
| S12 | 头前壳捕获相机；从外侧上方锁两枚 M2，再合后壳 | 不能夹住 FPC。壳缝孔已配对移动。不得把未设计完成的线束隐藏后宣布封壳完成。 |
| S13 | 头部总成与身体承重桥结合 | 裸转动座上方装入有检查；完整传动、服务环与固定点尚未完成，不能按裸座路径宣布完整总成已验证。 |
| S14 | 离机电池托盘放软垫、71×55×20 候选电池与绑带；滑入并锁两侧螺钉 | 轮子未装，下壳未封；先确认极性与串联保险丝方案，不能在接线未检查时接入电池。 |
| S15 | 下壳向上装入，再锁壳缝螺钉 | 先确认线束不进入拼缝及运动间隙。刚体下壳 120 mm 路径已有检查。 |
| S16 | 轮胎/轮毂及 10 mm 外隔套最后从左右套入；端部螺钉与垫片锁紧 | 两侧均有装入及整周转动检查。软胎材质、配合与轴端锁紧仍待物料/实物验证。 |
| S17 | 放在独立维护托架做无电手动行程、接线检查，再进入硬件上电流程 | 托架或插线时轮驱禁用；断电/急停由硬件交接确认。该文档不授权带电平衡试验。 |

## 插线与拆修

所有电源 PCB 的 XT30/XH/PH 对插件优先在承重桥、上壳和电池未装时插好，尤其 J2/J3/J4/J5/J10/J12。本次检查的是塑料壳的插拔空间，未把端子后方电线弯曲当作已经通过。电池、未选充电器、制动电阻的端点尚未固定；后板P5R7端点已收到，但其真实线束仍未完成，长度不能下料。

上壳与桥的相容顺序已由 `dual_body_sequence.json` 检查：先在台面把桥由下方放入上壳内部，分别托住；上壳保持绕身体中心 X 轴15°、向后14 mm的姿态，从上方下移，桥保持水平且其平移高度比上壳高4 mm。到上壳平移高度14 mm（桥18 mm）时，两者一起向前移14 mm；上壳保持15°/上移14 mm不动，桥单独下降18 mm进入主托架。此时装入并锁紧两枚M3，最后上壳沿15°/14 mm的联动反向就位，锁壳与框架螺钉。拆开时反向操作，头部转动总成先拆。共407个位置通过；螺钉25 mm抽出及长边内六角包络通过。

这个顺序需要独立支承上壳和桥，人工握持/夹具、线束随动仍为 NOT_TESTED。原整机动画没有表现这两个独立运动，不能直接按旧动画装这一步；本目录已补10秒独立动画body_sequence.mp4及可编辑body_sequence_animation.blend。已在P5R7独立接收模型上重跑同样407个位置和两处M3工具/抽出检查，均通过，见p5r7_receipt/dual_body_sequence.json。

## P5R7 核心板维护与接口限制

拆下头部转动总成、上壳后，三个原厂按键、USB外侧空间及E2/E4/E6/E7/E8临时弹簧探针上方通道通过包络筛查。工具尺寸要求记录在p5r7_receipt/service.json，并非已选定工具或已确认接触可靠性。核心板拔出还需要先拆承重桥；板子不能靠仍插合的公母针强扳。

官方STEP的E孔模型截面约Ø0.812 mm，候选直针为0.64 mm方针，其尖角对角线约0.905 mm。模型记录约0.123 mm³孔边重叠；不可扩孔、缩针或把STEP模型数值当实物孔公差。硬件第7项增补A1已直接核对官方STEP：原配弯针也是0.64 mm方针，原文件自身已有约0.122786 mm³孔边相交。故不能据此判定实物或新直针不合适，也不能批准插合。继续等成品孔与匹配针规格；机械主模型仍未替换。

## 工具约束

PH1 螺钉按 Wiha 42415/42416 的 Ø4 mm、60/80 mm 刀杆包络复核；壳体/框架较大螺钉按 PB190.2-100/6 包络。俯仰耳用 PB210.1.5（50×14 mm）长边进入、短边施力。其它 2/2.5 mm 内六角是明确记录的工具尺寸要求，并未假定已经买到。轴向工具可达不等于允许的拧紧转矩已知。

嵌件工具核查为 Ø3/4×10 mm 颈段、Ø7×35 mm 外筒和 Ø24×80 mm 手柄。选定热装头必须适配嵌件，不得只因外包络通过就确定温度或压力。逐项详细结果见 assembly_preflight.json。

## 仍不是只等实物的项目

头部舵盘/轴承/短轴传动接口资料；P5R7 E直针配合资料及接收候选正式应用；IMU和头部动态线束、固定点、插头后出线；充电模块/制动电阻/保险丝等未定端点。完整装配发布因此保持 BLOCKED。
'''
if full_animation_updated:
    process=process.replace('原整机动画没有表现这两个独立运动，不能直接按旧动画装这一步；本目录已补10秒独立动画body_sequence.mp4及可编辑body_sequence_animation.blend。',
        '完整装配动画已更新为 '+full_animation['animation_revision']+'，第9–11步表现这两个独立运动，第13–15步表现小舵机离机预装。完整视频使用'+full_animation['revision']+'主模型几何，没有混入P5R7候选。本目录另保留10秒独立候选动画body_sequence.mp4及可编辑body_sequence_animation.blend。')
if current_source!=source:
    process=process.replace('# M1.43 到货前装配工艺复核','# M1.43 到货前装配工艺复核（历史快照）\n\n当前主模型已更新至M1.44；本页载荷和线束等历史结果不自动延用。防脱连接与当前装配顺序见[本次报告](../../reports/头身防脱_M1_44.md)。')
(HERE/'ASSEMBLY_PROCESS.md').write_text(process)

requirements='''# 待补齐的厂家与硬件输入

本文件是要求清单，没有向厂家发出。第7项已有用户授权交硬件会话，P5R7已正式交接并完成下述独立几何复核；E直针/孔形冲突已在第7项范围内反馈硬件并收到增补A1：原厂STEP自带弯针同样与孔相交，实物孔和匹配针仍待厂家确认。充电模块、制动电阻等新增选型的交接正在等待用户答复。所有 hardware/ 与 contracts/components.json 保持只读。

## SCS0009

继续使用 SCS0009，不替换 SC09。FEETECH A/0 p3 给出 4.8 V 的 0.65 kgf·cm 表列转矩，p4/p6 有壳体与输出尺寸，但 p7 写明 No Accessories。现有资料不提供配套圆舵盘的完整安装数据；网页简介25T与尺寸资料20T存在版本矛盾，不能混用。

请提供实际供货版本的舵盘 STEP/正反面尺寸、齿形/有效啮合长度、完整轴向叠层、中心螺钉头型与最大旋入深度、连接孔网格和套装附件清单。详细询资料清单见 ../interface_completion/SCS0009_VENDOR_REQUIREMENTS.md。收到资料后还需完成承重短轴、轴肩、轴向保持及装配工具检查；当前四处传动锁紧不能生产放行。

官方资料：[产品页](https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html)、[A/0 PDF](https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf)。本地副本 mechanical/sources/v1_2/scs0009_spec.pdf 的散列在 manifest.json。

## S288

现有手册不能给出 9 V 连续允许转矩、转速/电流曲线和温升/工作制边界。请厂家补充这些数据，以及原厂六孔接口所需自攻螺钉的型号、有效啮合与允许锁紧要求。0.6 N·m 堵转/峰值不能直接当连续转矩。动态平衡所需储备不包含在本次纯行驶阻力估算内。

## 电气选型/线束端点

| 对象 | 需要的输入 | 收到后机械完成 |
|---|---|---|
| 第7项 WeAct E直针 | P5R7正式数据已收；核对0.64mm方针与原厂STEP中约Ø0.812mm孔的差异，确认配套针和实际孔规格 | 独立候选已查68针、130姿态、29插头、407装配位置及维护包络；E配合未定不能应用为已完成接口 |
| 外置3S充电模块 | 完整型号、输出方案、外形/高度、孔位、接插件/散热限制 | 安装位置/固定/通风与导线长度 |
| 外置5R6、10R制动电阻 | 封装与功率/脉冲要求、尺寸/引出、热隔离要求 | 空间与固定；不能把发热件贴在电池/PA12上假定安全 |
| 电池与串联保险丝 | 最终包体引线出口、对插件、保险丝/座外形及固定方式 | 电池拆修线长与实际支承/端点 |
| 9V/6V板端、电机和舵机端 | 选用焊线还是原厂插头、尾线型号、线规、绝缘外径与允许弯曲半径 | 有端子后直段、应力释放及双端端点的完整线束 |
| CAM/LCD/FPC | 原厂200mm 18p FFC 接触面与pin对应确认；相机FPC实际长度 | 折回和固定；不能仅因18pin相同就认定电气可互插 |
| 维护托架联锁、断电/急停 | 硬件接口和可操作执行件方案 | 开口/固定/触点空间；不会自行恢复已取消的开关孔 |

上述缺少资料项可以在到货前通过选型/厂家图纸解除，不应归类为仅等实测。电气电流、端子规格、线序由硬件定；机械不改电路或引脚来凑空间。
'''
(HERE/'INPUT_REQUIREMENTS.md').write_text(requirements)

# Complete branch inventory including local supplier harnesses not enumerated
# in the inter-board contract. Contract labels are preserved verbatim.
branches=[]
for r in routes['circuit_branches']:
    row=dict(r);row['mechanical_state']='端子后出线、固定点、线长仍待完成'
    if r['id'] in ['H01','H02','H03']:row['mechanical_state']='单束静态候选通过；未含端子后出线/固定/相互挤占'
    if r['id']=='H07':row['mechanical_state']='P5R7新位置/B面端点和插头已检查；下出线弯折、固定、实际线长未完成'
    if r['id']=='H04':row['mechanical_state']='IMU下穿路径弯曲未收敛；开口试案未通过，主件未改'
    if r['id']=='H05':row['mechanical_state']='同一8pin内分为两束4线的静态候选通过；分线区未定'
    if r['id'] in ['P_J11','P_J12','P_J1','H08','I01']:row['mechanical_state']='器件/引线/接口选型待硬件或用户确认'
    if r['id'] in ['H06','P_J9','P_J18']:row['mechanical_state']='跨头部运动接口；服务环进出、固定和完整动态路径待做'
    branches.append(row)
for i,a,b,note in [
 ('LOCAL_LCD','CAM33700 LCD','LCD35079','18p 0.5mm、随屏200mm FFC；端子方向/线序、折叠和固定未闭合'),
 ('LOCAL_CAMERA','CAM33700 camera','OV3660','原厂FPC长度/折弯/出口来自照片；等待匹配资料，不增加单独盖板'),
 ('LOCAL_SPEAKER','CAM onboard amplifier','SP3040','2线BTL输出；经过yaw和pitch两级有限运动，不能以公共地替代'),
 ('LOCAL_SERVO','SCS0009 yaw','SCS0009 pitch','同在yaw组；原厂尾线及串接端口位置待匹配供货版本')]:
    branches.append(dict(id=i,from_=a,to=b,status='BLOCKED',mechanical_state=note,length_mm=None))
(HERE/'harness_register.json').write_text(json.dumps(dict(source_blend_sha256=source,branches=branches,status='BLOCKED',cut_length_release=False),ensure_ascii=False,indent=2)+'\n')

def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
raw_path_rows=[[r['id'],r['status'],r['samples'],r.get('waypoint_displacements_mm') or r['withdrawal_axis']] for r in paths['cases']]
fast_rows=[[r['id'],r['status'],r.get('tool') or next((t['tool'] for t in r.get('trials',[]) if not t['hits']),''),r.get('stage',r.get('reason',''))] for r in asm['fasteners']]
display_routes=[dict(r) for r in routes['static_routes']]
for row in display_routes:
    current=next((x for x in replay['rows'] if x['id']==row['id']),None)
    if current:
        row['status']=current['status']
        if current.get('route_changed'):row['length_mm']=current['length_mm']
route_rows=[[r['id'],r['status'],f"Ø{r['bundle_diameter_allocation_mm']} / R{r['bend_radius_requirement_mm']}",f"{r['length_mm']:.1f}" if r.get('length_mm') else '未定', '已查静态包络；全线束未发布' if r['status']=='PASS' else '找到通道，但指定弯曲半径未能保留；未应用开孔' if r.get('reason') else ''] for r in display_routes]
branch_rows=[[r['id'],r['from_'],r['to'],r['mechanical_state']] for r in branches]
seqrows=[[r['id'],r['status'],r.get('samples',''),str(r.get('hits',[])[:1])] for r in seq.get('paths',[])+seq.get('order_alternatives',[])]
summary=dict(revision='V1.2-M1.43',source_blend_sha256=source,status='BLOCKED',geometry_changed=False,manufacturing_release=False,rigid_paths=len(paths['cases']),rigid_samples=sum(r['samples'] for r in paths['cases']),fasteners=asm['counts']['fasteners'],inserts=asm['counts']['inserts'],old_P5R6_plugs=asm['counts']['plugs'],scene_actor_coverage=200,full_harness='BLOCKED',assembly_order=dual['status'],assembly_order_samples=407,head_vendor_data='BLOCKED',hardware_issue7='BLOCKED: P5R7 received as independent candidate, E square pin versus vendor STEP hole unresolved',p5r7=dict(numbered_pins=len(receipt['numbered_pin_errors']),nominal_pinmap_max_error_mm=max(x['error_mm'] for x in receipt['numbered_pin_errors']),head_poses=130,head_collisions=len(receipt['motion_collisions']),mated_plugs=dict(collections.Counter(r['status'] for r in follow['mated_plugs'])),assembly_order=dual7['status'],assembly_positions=sum(x['samples'] for x in dual7['paths']),service_allocations=service7['status'],E_pin_pcb_overlap_mm3=sum(x['overlap_mm3'] for x in follow['E_pin_residual']),main_adopted=False))
summary['P5R7_static_route_replay']=dict(status=replay['status'],routes={r['id']:r['status'] for r in replay['rows']},cut_lengths_released=False)
summary['supplemental_animation']=dict(seconds=animation['duration_seconds'],frames=animation['frames'],main_full_animation_updated=full_animation_updated)
if full_animation_updated:
    summary['full_animation']=dict(revision=full_animation['animation_revision'],seconds=full_animation['duration_seconds'],frames=full_animation['frame_range'][1],stages=full_animation['stage_count'],body_sequence_readback=full_animation['body_sequence_readback'],geometry_source=full_animation['revision'],p5r7_adopted=False)
summary['P5R7_E_pin_fit_A1']=dict(status=a1['full_mated_fit'],source_model_internally_inconsistent=True,physical_hole_diameter_mm=None)
(HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 到货前装配与线束复核</title><style>
:root{color-scheme:light;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#263839;background:#f2f3ef}body{margin:0}main{max-width:1180px;margin:auto;padding:36px 24px 80px}a{color:#19645c}h1{font-size:32px;margin-bottom:12px}h2{font-size:23px;margin:0 0 18px}h3{font-size:18px}p,li{line-height:1.8}nav{display:flex;gap:20px;flex-wrap:wrap}section{background:white;border:1px solid #dbe1dc;border-radius:14px;padding:26px;margin:22px 0}.note{background:#fff4df;border-left:4px solid #c38a30;padding:15px 20px}.sequence{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.sequence figure{margin:0}.sequence figcaption{font-size:13px;padding-top:8px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{border:1px solid #dde5df;border-radius:10px;padding:18px}.card strong{display:block;font-size:28px;color:#2b7066}.card span{font-size:14px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #e2e6e2;text-align:left;padding:10px;vertical-align:top}th{background:#f5f7f3}td:first-child{white-space:nowrap}img{width:100%;height:auto;display:block;border-radius:6px}small,.muted{color:#5a6c6c}details{margin-top:18px}summary{cursor:pointer;font-weight:600;padding:12px;background:#f3f5f0}code{word-break:break-all}button{padding:8px 14px;border:1px solid #8ea69f;background:white;border-radius:6px;cursor:pointer}.tag{font-size:13px;padding:5px 9px;border-radius:5px;background:#e1ebe6} @media(max-width:700px){.sequence{grid-template-columns:1fr}.cards{grid-template-columns:1fr 1fr}main{padding:20px 12px}section{padding:18px}h1{font-size:27px}}@media print{details{display:block}details>*{display:block}button{display:none}section{break-inside:avoid}body{background:white}}
</style><main><nav><a href="../../index.html#interface">← 主模型 M1.43</a><a href="#assembly">装配</a><a href="#receipt">P5R7 接收</a><a href="#wiring">线束</a><a href="#load">载荷</a><a href="#inputs">待补资料</a><button onclick="window.print()">打印本页</button></nav>
<p class="muted">2026-10-01 · 当前收到版本的独立复核 · PROTOTYPE / UNVALIDATED</p><h1>到货前装配、线束与载荷复核</h1><p>已补查可用资料支持的刚体装入、工具空间与工程计算。主模型保持 M1.43。整机装配与线束仍有未闭合项，不能标记为“只等实物”。</p>
<div class="cards"><div class="card"><strong>26 / 2,087</strong><span>新增分件路径 / 离散位置</span></div><div class="card"><strong>69 + 4</strong><span>工具空间通过 / 等舵盘资料</span></div><div class="card"><strong>34</strong><span>裸件嵌件工具包络通过</span></div><div class="card"><strong>29 / 29</strong><span>P5R7 对插壳包络通过</span></div></div>
<section id="assembly"><h2>装配：补查顺序与工具空间</h2><p>俯仰舵机先从上方进入再横移就位；电源板插头在承重桥之前预插。离机锁紧、热装嵌件、线束连接和最后合壳分别列入工艺，不再只依赖爆炸动画。</p><p><a href="ASSEMBLY_PROCESS.md">完整工艺与工具要求</a> · <a href="assembly_coverage.csv">200 个场景对象工序清单 CSV</a> · <a href="assembly_preflight.json">逐紧固件与插头证据</a></p><div class="note">新增整机顺序检查：承重桥不能直接从已装身体上壳的上方插入；长边内六角工具也被上壳挡住。已找到不改外形的分步路径：上壳暂时抬高14mm、倾15°，桥保持水平单独落座并锁紧，最后合壳。P5R6及P5R7均重跑407个位置和工具空间通过；人工支承和线束随动待验证。</div>'''
page+=table(['采用的名义路径','状态','姿态数'],[[{'bridge_withdraw_18_shell_held_15deg_14up':'上壳保持倾斜抬起，桥单独落座','shell_and_level_bridge_back14_up140':'两件分别支承，共同下放再前移','shell_settle_with_bridge_fixed':'桥已固定，上壳回正落位'}[r['id']],r['status'],r['samples']] for r in dual['paths']])
page+='<p><a href="dual_body_sequence.json">P5R6证据</a> · <a href="p5r7_receipt/dual_body_sequence.json">P5R7的407姿态与工具证据</a></p><details><summary>被排除的简单装配路径及原因</summary>'+table(['顺序核查','状态','姿态数','首个碰撞证据'],seqrows)+'</details>'
page+='<details><summary>26 组刚体路径</summary>'+table(['操作','状态','抽样数','拆出轴/控制点；装入为反向'],raw_path_rows)+'</details><details><summary>73 处紧固件工具与台面阶段</summary>'+table(['紧固件','状态','工具','阶段/限制'],fast_rows)+'</details></section>'
page+='''<section id="receipt"><h2>P5R7 已收到：保留独立接收模型</h2><p>核心板按硬件会话中确认的<strong>元件面朝上、公针从背面向下</strong>重建；没有把整块PCB翻面。载板和后板取自正式P5R7，电源P5R6与IMU P5R4保持。候选板间距11.04 mm，未缩放原厂器件。</p><a href="p5r7_fit.png"><img src="p5r7_fit.png" alt="P5R7核心板元件面朝上，安装在独立接收候选中的排母上"></a><p>68针按针号对应，原生名义坐标与硬件交接表一致；130个头部组合姿态、29处对插壳和407个组合装配位置均已复核。J3改到后板背面并向下插拔后，旧位置的冲突解除。</p><div class="note">仍有一个真实资料差异：官方STEP里E孔截面约Ø0.812 mm，目录直针为0.64 mm方针，尖角对角线约0.905 mm，形成约0.123 mm³孔边重叠。这个STEP截面不是实物孔公差；没有擅自缩针或扩孔。硬件增补A1确认：原厂STEP自带的弯针也有同样相交，这是原模型内部不一致；它不能证明实物或新直针不能用，也不能作为插合通过的证据。成品孔径及匹配针仍待厂家资料，主模型及旧整机动画暂未替换为新板。</div><p>拆壳维护包络也已检查：三个板载按键、USB外侧和临时SWD探针通道可达；抽出核心板需先拆承重桥。这里用的是明确标尺寸的工具空间要求，不是已选工具、接触可靠性或插合保持力认证。</p><p><a href="../../../hardware/v1_2/reviews/weact_E_J3_20260930/E_pin_hole_addendum_20261001/README.md">硬件核对增补A1</a> · <a href="../../../hardware/v1_2/reviews/weact_E_J3_20260930/E_pin_hole_addendum_20261001/supplier_questionnaire.md">给WeAct的询问文本</a></p><p><a href="p5r7_received_preview.blend">独立Blender接收模型</a> · <a href="p5r7_fit.json">针位及整机碰撞数据</a> · <a href="p5r7_receipt/followthrough.json">对插与孔边证据</a> · <a href="p5r7_receipt/service.json">维护工具与E孔截面</a></p><h3 id="body-sequence">10秒补充装配动画</h3><p>橙色为承重桥：上壳先托住、桥水平落座、两侧M3锁紧，上壳最后就位。仅演示已检查的刚体顺序；未画入线束和人工支承，也未替代整机动画。</p><video controls playsinline preload="metadata" poster="body_sequence_poster.png" style="width:100%;max-height:650px;background:#343739" src="body_sequence.mp4"></video><p><a href="body_sequence_animation.blend">可编辑Blender动画</a> · <a href="body_sequence_animation.json">动画与源模型对应记录</a></p><details><summary>三步静态图</summary><p>① 上壳保持倾15°、上抬14 mm，桥保持水平、上抬18 mm；② 壳保持不动，桥单独落座，拧紧两侧M3；③ 上壳最后落下就位。两件必须分别支承，线束尚未画入。</p><div class="sequence"><figure><img src="body_sequence_1.png" alt="上壳倾斜抬高、承重桥保持水平抬高18毫米"><figcaption>① 上壳与桥分别托住</figcaption></figure><figure><img src="body_sequence_2.png" alt="桥已落座、上壳仍倾斜抬高"><figcaption>② 桥落座，趁上壳抬高时锁紧</figcaption></figure><figure><img src="body_sequence_3.png" alt="上壳已在承重桥锁紧后落下"><figcaption>③ 上壳最后就位</figcaption></figure></div></details></section>'''
page+='''<section id="wiring"><h2>线束：已有静态候选，尚未下料发布</h2><p>H01/H02/H03已有单束静态候选；H05有两束4线的候选，仍使用原来的8pin接头。收到P5R7后重查：H01原路径碰到抬高后的核心板，已局部绕行并复核；其余四条仍通过。本表通过的五条均有P5R7重查结果。长度只是当前中心线，不包含端子、应力释放和装配余量。IMU 支路的弯曲未通过；尝试的开口也未通过，未修改主托架。</p>'''+table(['线束','静态状态','假设包络 / 转弯','中心线 mm','范围'],route_rows)
page+='''<h3>头部服务环的空间筛查</h3><p>半径26 mm、高度165.5 mm 的 Ø3.2 mm 环形包络在130个头部组合姿态下未见碰撞。Ø5.2 mm 整束在筛查位置会碰承重桥或低头时的前壳。这个环只是可用空间，尚缺真实定长线束、固定点、进出路径与弯曲检查。</p><a href="neck_sections.png"><img src="neck_sections.png" alt="颈部不同高度的固定、转向、俯仰实体截面"></a><p class="muted">截面用于解释空间限制；不代表要按这些轮廓开孔。</p><details><summary>全部电气支路与本地排线</summary>'''+table(['ID','来源','目标','机械状态'],branch_rows)+'''</details><p><a href="harness_register.json">完整线束登记</a> · <a href="harness_routes.json">P5R6静态候选原始数据</a> · <a href="p5r7_receipt/route_replay.json">P5R7重查及H01新路径</a> · <a href="head_route_space.json">130姿态空间结果</a></p></section>'''
page+='''<section id="load"><h2>载荷：完成估算，保留资料边界</h2><p>现有模型估算约 <strong>1.30 kg</strong>，其中 PA12 实体约 <strong>0.75 kg</strong>；静态重心约在地面以上 <strong>110.9 mm</strong>，高于轮轴约58.4 mm。未计入尚未选型的充电模块、制动电阻及完整线束，不能称为最终整机质量。</p><img src="engineering_overview.png" alt="主要打印件质量与头部转矩筛查"><p>在1.35倍质量、假设线束拖曳和附加负载条件下，头部角加速度5 rad/s²时，俯仰/转向计算转矩约为 <strong>0.0274 / 0.0226 N·m</strong>。与 SCS0009 4.8V 表列0.65 kgf·cm（0.0637 N·m）的比值约2.33/2.82；它不是实测安全系数，也未验证舵盘、热性能或打印强度。</p><p>S288 的9V连续转矩/速度/温升数据仍缺失。纯行驶阻力计算没有替代自平衡控制、制动回馈或热验证。</p><p><a href="engineering.json">完整质量、惯量、390姿态与工况数据</a> · <a href="https://3d.ricoh.com/wp-content/uploads/2019/10/Ricoh-TDS-MJF-PA12-Web-Final.pdf">PA12 密度参考</a> · <a href="https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf">SCS0009 官方资料</a></p></section>'''
page+='''<section id="inputs"><h2>哪些仍能在到货前解决</h2>'''+table(['问题','下一步','当前状态'],[
 ['上壳/承重桥相容路径','分开支承，桥保持水平；P5R6和P5R7下407姿态均通过','PASS / 名义路径；人工操作待实物'],
 ['IMU/头部线束','完成端子后直段、弯曲、固定点、服务环及多线相互避让','BLOCKED / 机械设计未完成'],
 ['SCS0009 舵盘与轴向连接','获取匹配供货版本的完整尺寸，定型短轴与锁紧','BLOCKED / 等厂家资料'],
 ['硬件第7项','P5R7独立候选已完成几何接收；E方针与原厂STEP孔形冲突已反馈硬件','BLOCKED / E直针配合资料待核'],
 ['充电模块、制动电阻等','确定型号、尺寸和端点后完成空间/固定','BLOCKED / 等交接范围答复'],
 ['PA12 配合与强度、噪声、实测质量、动力学','到货及试打后按试片/装配工艺验证','NOT_TESTED / 需要实物']])
page+='''<p><a href="INPUT_REQUIREMENTS.md">厂家与硬件输入要求</a> · <a href="../interface_completion/SCS0009_VENDOR_REQUIREMENTS.md">SCS0009 详细询资料清单</a></p><p>没有向厂家发消息或下采购/打印订单。E直针配合差异已在原授权第7项内反馈硬件；充电模块/制动电阻等新增选型交接仍等用户答复。</p></section><section><h2>复现与版本</h2><p>所有结果由本目录脚本与日志生成；渲染对象仅在独立研究文件中创建。主模型未改动。</p><p>主模型 SHA-256：<code>'''+source+'''</code></p><p><a href="manifest.json">来源、输出散列、工具和命令</a> · <a href="summary.json">状态摘要</a></p><p class="muted">PASS 仅指对应范围的名义几何/计算检查。BLOCKED 表示缺资料或尚未闭合的设计，不等同于所有剩余事项都只能等实物。</p></section></main></html>'''
if full_animation_updated:
    page=page.replace('主模型及旧整机动画暂未替换为新板。','主模型和更新后的整机动画仍沿用旧板几何，P5R7未应用。')
    page=page.replace('未画入线束和人工支承，也未替代整机动画。','未画入线束和人工支承。完整装配视频现已并入相同的分步顺序，<a href="../../animation/index.html?revision='+full_animation['animation_revision']+'">查看更新后的'+str(full_animation['duration_seconds'])+'秒整机动画</a>；完整视频保持M1.43主模型，本段补充动画使用独立P5R7候选。')
(HERE/'index.html').write_text(page)
if current_source!=source:
    page=page.replace('<h1>到货前装配、线束与载荷复核</h1>', '<h1>到货前装配、线束与载荷复核（M1.43历史记录）</h1><p class=notice>当前主模型已采用M1.44头身防脱压板。本页载荷、线束等证据属于M1.43快照，不自动延用为新模型通过。<a href=../../index.html#head-retention>查看M1.44防脱更新及复核</a>。P5R7仍是独立候选。</p>')
    page=page.replace('主模型保持 M1.43。','本页研究基准保持 M1.43。')
    page=page.replace('完整视频保持M1.43主模型','完整视频使用M1.44主模型')
    page=page.replace('← 主模型 M1.43','← 当前主模型')
    (HERE/'index.html').write_text(page)
(HERE/'README.md').write_text('''# 到货前复核（M1.43）

先看 [可视化审查页](index.html)、[装配工艺](ASSEMBLY_PROCESS.md)、[输入要求](INPUT_REQUIREMENTS.md)。完整工艺和线束仍为 BLOCKED；主模型与硬件源文件未改。

`engineering.py` 计算现有模型质量/惯量及头部、行驶工况；`assembly_preflight.py` 查分阶段工具/嵌件/插头；`rigid_assembly_paths.py` 查26组刚体路径；`sequence_dependencies.py` 查这些步骤能否组成真实装配顺序；`harness_routes.py` 只生成候选线束；`head_route_space.py` 只筛查服务环空间。`dual_body_sequence.py` 补充407个两件独立运动的装配位置；`receive_p5r7.py` 从只读原生板重建P5R7缓存；`p5r7_fit.py`、`p5r7_followthrough.py`、`p5r7_service.py` 校核独立接收候选。`body_sequence_animation.py`生成10秒补充Blender/MP4动画，不替代旧整机动画。各自同名JSON与log是证据。

`imu_feedthrough_candidate.blend` 是未采用且未通过的独立尝试，不得导出为当前制造件。`lcd_diagnostic.*` 是隐藏代理变换的诊断，确认主模型 LCD 没有该假象碰撞；不需要改 LCD。`neck_sections.svg.png` 为不完整的 QuickLook 缩略图，不用于交付；使用完整的 `neck_sections.png`。

重新生成审查页：`/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_closure/publish.py`。几何脚本需由 Blender 打开 `mechanical/mori_v1_2.blend` 后运行，实际命令与版本见 manifest.json。
''')
files=[p for p in HERE.rglob('*') if p.is_file() and p.name not in ['manifest.json','publish.log'] and '__pycache__' not in p.parts]
if full_animation_updated:
    readme=HERE/'README.md'
    readme.write_text(readme.read_text().replace('不替代旧整机动画。','完整整机动画已另行更新至'+full_animation['animation_revision']+'，沿用主模型几何。'))
manifest=dict(date='2026-10-01',revision='V1.2-M1.43',source_blend_sha256=source,hardware_contract_at_study_start_sha256='f97b95addee1708530ba05247e3012e7525fa2666af5c31d970c37b037433b36',hardware_contract_at_publication_sha256=digest(ROOT/'contracts/components.json'),electrical_contract_used_by_routes_sha256=routes['electrical_contract_sha256'],electrical_contract_at_publication_sha256=digest(ROOT/'contracts/electrical_interfaces.json'),software=dict(blender='5.2.2 LTS d13f752e3b9c',python='mori-cad runtime; see tool_versions.txt',manifold='3.5.3',matplotlib=matplotlib.__version__),commands=[f'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_closure/{n}.py > mechanical/studies/prearrival_closure/{n}.log 2>&1' for n in ['engineering','assembly_preflight','rigid_assembly_paths','harness_routes','head_route_space','neck_sections','inspect_lcd','imu_feedthrough_candidate','sequence_dependencies','dual_body_sequence','p5r7_fit']],postprocessing=['Corrected contiguous tool angle from N samples to (N-1)*2deg using recorded collision samples; no geometry changed.','Verified each passing static path is reproduced by the declared analytic radius arcs; resampled circumradius remains diagnostic only.'],source_files={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'mechanical/sources/v1_2/scs0009_spec.pdf',ROOT/'mechanical/sources/v1_2/unitree_servo_manual.pdf',ROOT/'mechanical/sources/populated_P5/inventory.json',ROOT/'hardware/v1_2/handoff/mechanical_P5R7.json',ROOT/'hardware/v1_2/reviews/weact_E_J3_20260930/weact_alignment_audit.json',a1_path]},files={str(p.relative_to(HERE)):digest(p) for p in files})
manifest['commands'] += [
 '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 mechanical/studies/prearrival_closure/receive_p5r7.py inventory > mechanical/studies/prearrival_closure/p5r7_inventory.log 2>&1',
 '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 mechanical/studies/prearrival_closure/receive_p5r7.py export > mechanical/studies/prearrival_closure/p5r7_export.log 2>&1',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_closure/receive_p5r7.py convert > mechanical/studies/prearrival_closure/p5r7_convert.log 2>&1',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_closure/receive_p5r7.py supplement > mechanical/studies/prearrival_closure/p5r7_supplement.log 2>&1',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_closure/p5r7_fit.blend --python-exit-code 1 --python mechanical/studies/prearrival_closure/p5r7_followthrough.py > mechanical/studies/prearrival_closure/p5r7_followthrough.log 2>&1',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_closure/p5r7_received_preview.blend --python-exit-code 1 --python mechanical/studies/prearrival_closure/p5r7_service.py > mechanical/studies/prearrival_closure/p5r7_service.log 2>&1',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_closure/p5r7_received_preview.blend --python-exit-code 1 --python mechanical/studies/prearrival_closure/body_sequence_animation.py > mechanical/studies/prearrival_closure/body_sequence_animation.log 2>&1',
 '/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_closure/p5r7_received_preview.blend --python-exit-code 1 --python mechanical/studies/prearrival_closure/p5r7_route_replay.py > mechanical/studies/prearrival_closure/p5r7_route_replay.log 2>&1',
 '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_closure/publish.py > mechanical/studies/prearrival_closure/publish.log 2>&1'
]
manifest['P5R7_receipt']={'handoff_sha256':receipt['handoff_sha256'],'status':'BLOCKED','main_adopted':False,'source_STEP_hole_model_vs_square_pin':'A1 received: original bent pin already intersects vendor STEP holes; finished holes and matched pins remain unknown, not a proven incompatible physical part.','addendum_sha256':digest(a1_path)}
(HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('PUBLISHED',summary)
