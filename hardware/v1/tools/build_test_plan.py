#!/usr/bin/env python3
import csv,json
from pathlib import Path
H=Path(__file__).resolve().parents[1]
tests=[]
def add(id,name,pre,op,equipment,observe,accept,stop,risk):
    tests.append(dict(id=id,test=name,status='NOT_TESTED',prerequisites=pre,operation=op,equipment=equipment,observables=observe,pass_criteria=accept,stop_conditions=stop,risk=risk,
       record_fields='date/operator/serial/PCB_rev/BOM_rev/firmware_hash/instrument_calibration/supply_limit/AmbientC/V/I/temperature/time_series/log_path/photos/result/stop_reason',results='',evidence=''))
add('T00','断电检查','电路/封装/连接器图冻结，器件实物与BOM相符','逐网导通与极性；电池未接；短路/焊桥/端子防呆/绝缘/线束拉力检查','DMM、放大镜、原理图、压接工具','各轨对地阻值、保险、回流、DC连接器极性','与网表一致；无低阻短路；功率线不经逻辑板；孔位不压线','任何不明引脚/极性/器件后缀','反接、瞬时短路、压线')
add('T01','限流首次供电','T00 PASS；电池/电机/舵机拔除；外部托架','从限流0.1A开始，只逻辑空载；逐步到所需供电，不以加大限流掩盖异常','可调限流电源、DMM、示波器、热像','输入电流、轨启动/纹波、器件温升','无异常限流/热升；设计输出容差与启动顺序满足','未知发热、周期复位、异味或输入异常','焊错损坏；不可直接上电池')
add('T02','两逻辑轨及断电隔离','T01 PASS；执行器硬件断能','依次开关两域、拉EN/BOOT、USB夹具插拔；模拟交互短路限流','双通道电源、示波器、电流计','3V3、EN、UART电位、关断域漏电、本地循环','3.3V目标±5%，无越过芯片上限；交互复位不复位运动；无输出使能；关断漏电符合所选器件数据手册','运动掉电/使能毛刺/关断域被抬电','假隔离、反灌PC USB；门限为设计验收值非实测')
add('T03','单外设与IMU','T02 PASS；固定机身且电机拔除','逐个枚举IMU/INA/LCD/相机/音频；六面静置IMU并轻转轴','逻辑分析仪、示波器、参考姿态夹具','WHO_AM_I、数据率、DRDY→时间戳/控制读取年龄、轴向与噪声','SPI无错误；目标500Hz控制时样本年龄≤3ms；机身前倾为-X；静态量与量程相符','不明WHO_AM_I/陈旧样本被接受/轴向错','坐标或单位错误导致正反馈')
add('T04','单电机悬空与协议/电流','T03 PASS；轮悬空、限流电源、独立急停和外部防护；驱动SKU规格已齐','从最小命令短时正反转，记录电流与速度；FOC分别核协议模式/数值符号；不堵转','电源、示波器、LA、电流探头、转速计','帧字节、线电平、实际相电流/母线电流、位置速度、指令延迟','单位和模式获得证据；命令撤销/看门狗/急停按定义失能；无越额定','未知单位、无反馈、延迟异常、电流超初始限值','快速甩轮/电流伤害；不得将tor整数认作Nm')
add('T05','编码器倍频与左右符号','T04 PASS；驱动禁能可手转','分别正向轮转10圈，数AB/位置计数；反向并慢速过零；再低速通电比对','LA、轮标记、转台/转速计','A/B周期、x1/x4差异、计数每圈、方向、速度更新时间','左右使机器人+Y运动时反馈均正；重复计数一致；PPR矛盾有厂家或实测结论','漏计、相位不稳、逻辑幅度越3.3V容限','方向误配导致平衡发散')
add('T06','双轮同步与限幅','T05 PASS；两轮悬空','逐步驱动同向/反向，模拟串口丢包、重启、缓冲洪泛和急停','LA、示波器、限流电源','两轮反馈年龄、抖动、CRC、命令租期、输出使能','运动环不阻塞；失联≤200ms取消导航，租期≤300ms；不自动重启驱动','旧命令续租/任一轮无反馈仍加力','异步、无线噪声误触；仍不接地跑动')
add('T07','制动/回灌','T06 PASS；消能电路额定通过计算；电池不直接代替可测电源；防护罩','低速低能量起逐步制动；仿真满电不吸收场景；验证buck两侧和夹位','可吸能电源或已设计制动负载、差分探头、电流探头、热像','轮母线与电池母线峰值、消能脉冲、MOS/电阻温升','均低于最弱器件额定含裕量；断电反灌受控；重复制动热稳态通过','超过暂定保护阈值/消能失效/温升持续上升','过压烧毁、热损坏；不得以电源能吸能掩盖电池不能吸能')
add('T08','舵机并发、反馈与线束','T07 PASS；头部承载轴承/极限机构已检查；车身托架','先卸载中心小角度，再带头部组合yaw/pitch；反馈多点双向标定；短脉冲测峰值不持续堵转','示波器、量角夹具/光学参考、电流计、声级计','PWM/FB、5V纹波、轨间干扰、回差、噪声、保持电流、机身IMU噪声','有效行程覆盖机构要求，无硬碰；反馈单调/误差记录；视角投影按实测误差保守处理；无欠压','反馈饱和/接近机械止点/线缆拉紧/轨掉压','头部夹手、舵机过载、线束扭断')
add('T09','机械轮轴/摩擦/齿隙','T08 PASS；关电安全支撑','测轮侧载/轴承间隙/反向死区/轮胎摩擦；核皮带预紧和轮轴轴向锁止','力计、百分表、扭矩臂、秤','径向挠度、齿隙角、起动电流、摩擦系数、轴承热','更新动力模型参数；实际额定/安全系数通过；无卡滞/松脱','轴裂/轮滑移不可控/卡滞','夹手、破片；不能长时间堵转测扭矩')
add('T10','平衡台架','T09 PASS；实测系统辨识、限幅/延迟已更新；参数非直接复制Hover','低角度0.5–2°起，以外部铰架/松弛保护绳限跌落；逐步增加扰动；确认控制符号','限流电源、独立急停、保护台架、数据记录','姿态、轮速、电流、饱和比例、轨压、实际控制/反馈时延','预先定义角度/速度/电流包络内收敛，安全故障路径有效；无连续饱和','角速度增长、饱和持续、反馈陈旧、松绳受力','台架可能改变动力学；不得把台架PASS当自由站稳')
add('T11','外部保护实机','T10 PASS；空旷平地无人接近、外部软防护、急停可及','初始无导航健康平衡；再0.1m/s/≤0.3m受控段；切交互电源/网络/相机','隔离防护区、松弛捕获装置、遥测与摄像','实际接触数、跌落/饱和、停目标响应、供电','运行时只有两轮接地；导航失联归零仍健康平衡；无自动重解锁','保护绳受力、越界、跌倒、未授权继续行驶','跌落；无专用避障/防跌落能力，不在人/台边测试')
add('T12','音视频视觉并发压力','T11 PASS；摄像头实际模式与反馈角度标定','显示双眼+QVGA持续采集/人脸检测+I2S录播/AEC+Wi-Fi，同时平衡和小幅转头','trace、LA、离线标注视频、音频参考、功率计','帧率/p95观测年龄、PSRAM峰值、DMA丢帧、控制抖动、ERLE/误唤醒','目标观测年龄≤250ms；不满足即停止视觉导航并报告；运动样本年龄不恶化；AEC输入含真实播放参考','OOM/队列堵塞/用旧帧续命令/声反馈啸叫','人脸≠全身跟随；并发未测前不能宣称支持视频跟随')
add('T13','USB-C充电与保护','电池厂家充电/均衡/保护参数齐全；充电链图纸已审核；托架、系统断开','分别验证默认/1.5A/3A广告、插拔、输入不足、终止再充；测试仪验证双节电压','Type-C协议/电流测试仪、功率计、DMM、热像','CC/VBUS、输入限流、8.4V CC/CV、单节电压、温度、终止条件','从不超源广告/电池厂家限值；系统及执行器禁用；充电保护/均衡策略满足包规格','任一节超限、温升异常、未识别源仍满功率取电','充电故障；未知厂家限制时不执行此项')
add('T14','60分钟混合续航','T11–T13 PASS；所有材料到货；电池容量/内阻实测；完整机壳','持续平衡+相机+眼睛；累计10min移动/10min语音；每分钟小转头；固定亮度音量与联网条件','积分功率计、逐节电压工具、时间记录、热像','Wh、平均/峰值W、最低轨压、BMS事件、温升、头姿态/语音/画面占空比','连续≥60min，功能占空比达标，未触发BMS断电、危险温升或非预期复位；余量完整记录','低电预警、压降余量不足、温度上升、容量明显异常','不得为凑60min关闭必需负载或靠BMS突然断电结束')
with (H/'test_plan.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(tests[0]));w.writeheader();w.writerows(tests)

h=[]
def harness(id,qty,pins,device,wire,current,route,note):
    for n,signal in enumerate(pins,1):h.append(dict(revision='V1-H0.1',harness_id=id,quantity=qty,carrier_candidate_pin=n,signal=signal,device=device,
      device_pin='UNKNOWN_UNTIL_VENDOR_DRAWING',wire=wire,current_basis=current,routing=route,status='BLOCKED_NOT_FOR_WIRING',notes=note))
harness('BAT',1,['BAT_PLUS','GND'],'ANSMANN2447-0105 factory keyed XT30 termination','20AWG stranded copper','5A candidate pack upper limit, not proved continuous','short near fuse; separate high-current return','Do not solder bare cells. XT30 gender/polarity drawing and pack discharge spec must match.')
harness('FOC',2,['WHEEL_BUS','GND','DATA_TX','DATA_RX'],'unknown4012FOC','20AWG power;26AWG signal twisted with GND','UNKNOWN motor rating','left/right labelled, keep signal separate from motor phases','Not vendor pinout. Half/full duplex and logic unknown: no assembly release.')
harness('ENC_ALT',2,['ENC_3V3','GND','A','B'],'FIT0521 encoder portion of PH2.0-6P','26AWG','logic only','AB with ground reference; shield termination if measurements require','Actual motor6pin order and colors unknown. Keep motor wires separately rated; do not crimp from this table.')
harness('MOTOR_ALT',2,['OUT1','OUT2'],'FIT0521 motor portion','22AWG minimum candidate','hardware limit1.5A target','twisted pair; suppress at motor per vendor EMC guidance','Polarity sign assigned only after T05. No direct battery.')
harness('SERVO_YAW',1,['SERVO_5V','GND','PWM_YAW','FB_YAW'],'FT90M-FB','24AWG power;28AWG signals','1A per servo transient design bound','finite yaw loop; clamp strain relief','Vendor4wire order/colors not published in reviewed PDF; must confirm.')
harness('SERVO_PITCH',1,['SERVO_5V','GND','PWM_PITCH','FB_PITCH'],'FT90M-FB','24AWG power;28AWG signals','as yaw','pitch loop, all combined poses','Same warning; no PWM-only substitute without contract change.')
harness('LCD',1,['3V3_I','GND','MOSI','SCLK','CS_N','DC','RST_EN','BL'],'Waveshare19192','28AWG signal + adjacent ground','31.2mA reference, measurement pending','candidate<80mm; start20MHz; keep away servo wiring','Physical8pin order must be verified; diagram signal order is not vendor index.')
harness('IMU',1,['3V3_M','GND','SCK','MOSI','MISO','CS_N','INT1'],'Adafruit4438','28AWG short','logic only','rigid body, target<50mm','Avoid flexible shell mount. Vendor SPI labels mapped to own netlist before assembly.')
harness('MIC',1,['3V3_I','GND','BCLK','WS','SD','LR_GND'],'SEN0327','28AWG','logic only','away classD/servo, small isolation gasket','LR ground selects left; manufacturer actual wire order needed.')
harness('AMP',1,['5V_AUDIO','GND','BCLK','WS','DIN','ENABLE'],'DFR0954','24AWG supply;28AWG logic','speaker cap.25W RMS, amplifier supply margin','close speaker; away mic','SD control voltage behavior/board pullups verify, external pulldown keeps boot muted.')
harness('SPK',1,['BTL_OUT_PLUS','BTL_OUT_MINUS'],'Adafruit1890','26AWG twisted pair','8ohm .25W rated','short away IMU/mic','Neither lead to ground; max0.5W is not continuous.')
harness('MCU_LINK',1,['GND','M_TX_I_RX','I_TX_M_RX'],'two domain translators at carrier','28AWG','3.3V logic','local body, no unisolated supply wire','No UART0 reset/boot coupling.')
harness('DEBUG',2,['GND','3V3_SENSE','D_MINUS','D_PLUS','EN','BOOT_N'],'hidden keyed pogo jig','short USB controlled pair','SENSE not external power','maintenance cradle only','No exterior second/third USB-C; jigVBUS not tied to robot rails.')
with (H/'harness.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(h[0]));w.writeheader();w.writerows(h)
print(f'{len(tests)} physical tests NOT_TESTED; {len(h)} candidate harness terminal rows blocked pending vendor pinouts.')
