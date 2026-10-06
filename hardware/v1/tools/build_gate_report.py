#!/usr/bin/env python3
import csv,json
from pathlib import Path
H=Path(__file__).resolve().parents[1]
if json.loads((H/'bom_candidates.json').read_text()).get('revision') != 'V1-H0.1':
    raise SystemExit('H0.1 gate report is historical; use procurement/BOM_国内采购核验.md for current domestic evidence and budget policy.')
def read(n):return json.loads((H/'reports'/n).read_text())
b=read('budget.json');p=read('power_energy.json');m=read('mass_inertia.json');d=read('dynamics_sweep.json')
f,a=b['routes']['FOC'],b['routes']['BRUSH']
conflicts=[
 ('G01','预算','BLOCKED',f"FOC已知标价折算{f['assumed_fx_known_subtotal_cny']:.2f}元，{f['unknown_count']}行未核价；含未知额度情景{f['scenario_with_unquoted_allowances_cny']:.2f}元，较900/1000高{f['scenario_over_900_cny']:.2f}/{f['scenario_over_1000_cny']:.2f}元",'取得国内真实单只报价、到货运税、PCB组装/打印费用；不增预算、不删功能地重新选有证据部件'),
 ('G02','FOC轮驱','BLOCKED','4012无完整后缀/尺寸/连续能力/报价/raw单位；轮毂直驱与现皮带结构不同','供应商型号图纸、驱动固件协议和可靠采购报价；轮胎/轴接口机械更新'),
 ('G03','有刷备选','FAIL',f"已知标价{a['assumed_fx_known_subtotal_cny']:.2f}元（假设汇率），未计{a['unknown_count']}行即超1000；厂家PPR/功率点不自洽",'不视为已选；新报价与厂家数据澄清，台架辨识与控制接口重新适配'),
 ('G04','舵机/显示机械','FAIL','FT90M-FB含耳/花键32.6×12.19×28.55；屏幕活跃Ø32.4≠58','机械任务按真实包络改支架/眼睛/开口，组合角度线束碰撞校核'),
 ('G05','电池与板框净空','BLOCKED','39×71×18仅核心近似可入；线束/减振/拔插额度不足；96×76载板未布局','机械确认新服务包络、中央避让、模块天线净空与板孔坐标'),
 ('G06','电池/充电/均衡','BLOCKED','成品包保护阈值、均衡/回灌与充电限值未知；DFR0564无均衡/LOAD；8.4V±1%上界8.484V须与包规格核对','匹配的成品2S保护/充电资料；核单节及总压上界、CC/CV和终止逻辑，或更换匹配套件'),
 ('G07','并发电流','FAIL','模型33.78W/6.4V≈5.28A，超过候选包网页5A；未计未知电池内阻压降','额定连续数据、硬件限流/支路优先级与负载并发实测，验证低压稳压余量'),
 ('G08','回灌/急停/电源路径','BLOCKED','轮母线额定未知，主动消能、保险反接、急停/watchdog具体后缀未冻结','器件额定与失效路径原理图；就地消能能量/温升校核，禁止靠BMS突然断电'),
 ('G09','摄像头与音频电气','BLOCKED','M0031完整24pin/FPC/电源缺图；音频5V掉电时I2S隔离未核；若摄像头IO1.8V需全数据电平转换','原厂模组图、接触面/各电源、输入容限；Ioff缓冲与模块真实连接器映射'),
 ('G10','供应和自定义唤醒','BLOCKED','扬声器1890缺货；FT90M-FB报价未知；MORI真实唤醒模型未交付','可靠供应报价；免费社区模型实际取得或专属定制报价/交付，不改名冒充模型'),
 ('G11','硬件能力与续航','NOT_TESTED','所有电流/温升/反馈/回差/站立/音视频并发/续航均无实物记录','按T00–T14逐项记录，不把仿真或资料标价当实测'),
 ('G12','V1原理图/PCB/ERC/DRC','BLOCKED','KiCad10.0.6可用；用户规定的上游门槛失败，本轮未创建新V1原生工程、未执行V1 ERC/DRC','上述预算/包络/器件接口通过后绘原生图，布线完成真实跑ERC/DRC，明确PROTOTYPE再导出')]
with (H/'conflicts.csv').open('w',newline='',encoding='utf-8-sig') as out:
    w=csv.writer(out);w.writerow(['id','scope','status','evidence','release_condition']);w.writerows(conflicts)
masslines=[]
for row in m['scenarios']:
    if row['yaw_deg']==0 and row['pitch_deg']==0:
        q=row['parameters'];masslines.append(f"|{row['case']}|{q['total_mass']:.2f}|{q['body_mass']:.2f}|{q['wheel_mass']:.2f}|{q['l']*1000:.0f}|{q['Jbody']:.2g}|")
text=f'''# MORI V1-H0.1：第一道硬件门槛报告

日期2026-09-21。**结论：预算、包络与电源接口未通过，不能释放采购或V1定板。任务2尚未全部完成。** 已完成真实候选资料核对、可运行模型、机械/电气候选契约、引脚和线束边界、测试计划及软件并行交接。原A0工程保留，未改成新V1证明。

主路线保留两只带真实反馈的FOC轮驱 + 两只FEETECH FT90M-FB头部位置舵机、两颗ESP32-S3-WROOM-1-N16R8，以及圆屏/摄像头/麦克风/扬声器/机身IMU/电源监测/按钮/USB-C。没有删成三执行器或单MCU。仅保留FIT0521+DRV8874为一套关键替代；尚未切换主路线。

## 预算实际算到哪里

|路线|有公开标价部分，按假设汇率折算|未核价行数|加未报价额度的情景总额|情景超过900 / 1000|
|---|---:|---:|---:|---:|
|FOC条件主路线|¥{f['assumed_fx_known_subtotal_cny']:.2f}|{f['unknown_count']}|¥{f['scenario_with_unquoted_allowances_cny']:.2f}|¥{f['scenario_over_900_cny']:.2f} / ¥{f['scenario_over_1000_cny']:.2f}|
|有刷唯一备选|¥{a['assumed_fx_known_subtotal_cny']:.2f}|{a['unknown_count']}|¥{a['scenario_with_unquoted_allowances_cny']:.2f}|¥{a['scenario_over_900_cny']:.2f} / ¥{a['scenario_over_1000_cny']:.2f}|

USD7.2、EUR8.0均为规划汇率假设，非实时外汇报价。FOC已知小计原币：CNY {f['public_list_subtotals']['CNY']:.2f} + USD {f['public_list_subtotals']['USD']:.2f} + EUR {f['public_list_subtotals']['EUR']:.2f}。未知费用留null，不按0算通过。情景总额含线束/端子/PCB及组装/打印材料/运费的暂定额度，但未取得完整到货报价，也未证明外包打印成本；100元风险余量尚未另加进去。故“超额”是此候选情景的量化差距，不是精确成交超支。

首台没有任何必要部件按“已有免费”记账。打印料采用机械网格490.65g×1.2支撑废料+150g托架/试打，假设70元/kg约51.71元，预算额度取52元。新FOC两驱含固件/驱动价格未知，不能拿280元规格分配冒充报价。当前完整方案不能声明≤1000元成立。

## 质量、动力与续航

|当前皮带布局需求情景|整机kg|被平衡机身kg|旋转轮系kg|机身COM高于轴mm|机身COM俯仰惯量kg·m²|
|---|---:|---:|---:|---:|---:|
{chr(10).join(masslines)}

这些是机械网格和有来源/显式假设的器件质量组合，含线束/载板，不是称重结果。4012实际轮毂位置未知，不能把这张表当其完整装配惯量。15组头姿态结果与原点惯量转换校核已保存。头部假设机身±10°倾斜、60°/s²加速度和线缆/轴承阻力后，最大需求约pitch{max(x['pitch_required_Nm'] for x in m['head_loads']):.3f}Nm/yaw{max(x['yaw_required_Nm'] for x in m['head_loads']):.3f}Nm；5V舵机连续性能和回差仍需实测，不能由6V堵转值宣布足够。

95mm轮径：0.10m/s≈20.1rpm/2.11rad/s；0.30m/s≈60.3rpm/6.32rad/s。供应商PPR算式错误，倍频常数未冻结。理想动力学包含轮转动惯量、机身反力矩、饱和、命令延迟、一阶执行器、摩擦和死区，27组合中{sum(x['criterion_met'] for x in d['runs'])}组满足所设仿真收敛判据；这是对时延/力矩余量的敏感性结果，**不是站稳验证或可上传增益**。[查看时延敏感性图](reports/delay_sensitivity.png)。

电池24.12Wh扣可用SOC/容量余量得到17.37Wh。负载5.34/7.34/11.34W情景对应约195/142/92min，未知实际轮驱损耗足以改变结论；平均20W则约52min。60分钟验收仍为NOT_TESTED。并发峰值约33.78W/5.28A已触碰候选电池限制，必须先解决。回灌算例约0.19J，而1000µF在8.4→8.8V仅吸收0.00344J；不能省略主动消能或经验证的电池吸能路径。

## 装配与电路的关键阻塞

1. 4012只是一条参考名称，没有完整型号、尺寸、连续能力、价格和协议单位；当前机械是抬高电机皮带方案，轮毂直驱需要重新定义安装。
2. 两舵机含耳/花键32.6×12.19×28.55mm超过预留；圆屏真实显示Ø32.4mm与模型58mm不一致；充电28×37mm、测流30×22mm没有现成合格空间。电池只有裸包核心接近可容，线束净空未通过。
3. 2S保护包、非均衡充电器、USB-C电流识别、充电系统断开、急停/看门狗、反接/保险、回灌、掉电信号隔离仍需完成器件匹配与原理图审查。8.4V±1%充电上界8.484V也须对照电池允许值。
4. 摄像头M0031的24pin/FPC/电源图尚缺；不得从“OV2640支持”跳到“已经能并发视频跟随”。自定义MORI唤醒需要真实模型，免费社区路线有交付不确定性，付费路线未报价。

逐项责任数据和解除条件见 [conflicts.csv](conflicts.csv)；机械任务输入见 [mechanical_handoff.md](mechanical_handoff.md)。原机械分配字段未改，供应商实际数据单独写共享契约；未拿假孔位填null。

## 交付与验证边界

- [候选BOM CSV](bom_candidates.csv) / [可计算JSON](bom_candidates.json)：28条主件/备选/必需费用条目，公开价格与额度分栏，工程包仍需展开成最终采购料号。
- [可运行模型说明](calculations/README.md)：预算、质量/重心/惯量、轮速、27组动力学、低压敏感性、头部负载、能量/回灌、打印料计算。
- [共享机械契约](../../contracts/mechanical_interfaces.json) / [共享电气契约](../../contracts/electrical_interfaces.json) / [版本化pinmap](interfaces/pinmap_V1-H0.1.csv)：82条模块pad记录，候选未释放。
- [电源树与接线约束](power_and_wiring.md) / [线束表](harness.csv) / [双MCU协议](link_protocol.md) / [音视频资源](media_resources.md)。58个载板侧候选端子定义；设备端未知脚序明确禁止带电照接。
- [15项实测计划](test_plan.csv)：每项前置、操作、设备、观测、通过/停止条件、风险和记录栏齐全，均NOT_TESTED。
- [软件并行提示词](software_parallel_prompt.md)：现在即可交给任务3做协议、安全状态机、mock与构建，不等待采购，也不擅自驱动实物。
- [参考审计与许可](reference_audit.md)；[真实工具/验证状态](reports/validation_status.json)。文件一致性检查PASS，不是电路资格认证。

**KiCad10.0.6已核验，V1原生原理图/PCB尚未创建，ERC/DRC未执行、结果为null，制造文件未导出。** 这是遵守先预算和包络后电路的顺序；不是工具缺失，也没有把文字框图或旧A0工程冒充新V1工程。取得上述缺失的供应商规格/报价并通过机械、电源门槛后，才可以进入原生电路、封装校验和可验证PCB阶段。未采购、未下单、未烧录。
'''
(H/'README.md').write_text(text)
print('Updated V1 gate report and 12 explicit conflicts.')
