#!/usr/bin/env python3
"""Generate the auditable V1 candidate register. No purchase authorization."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'hardware/v1'
DATE = '2026-09-21'
REV = 'V1-H0.1'
if (OUT/'bom_candidates.json').exists() and json.loads((OUT/'bom_candidates.json').read_text()).get('revision') != REV:
    raise SystemExit('H0.1 generator is historical. Use tools/build_domestic_bom.py; refusing to overwrite a newer BOM.')
rows = []

def add(id, purpose, qty, model, voltage, dimensions, mass, interface, source,
        price=None, currency='CNY', route='COMMON', cap=None, note='', channel=None):
    rows.append(dict(id=id, route=route, purpose=purpose, quantity=qty, model=model,
        voltage_or_rating=voltage, vendor_dimensions_mm=dimensions, vendor_mass_g=mass,
        shaft_hole_interface=interface, source_url=source, accessed=DATE,
        procurement_channel=channel or source or '待提供可核验渠道',
        unit_price=price, currency=currency, price_date=DATE if price is not None else None,
        price_status='PUBLIC_LIST_PRICE_NOT_LANDED_QUOTE' if price is not None else '待核价',
        shipping_basis='未含中国目的地运费/税费；合并运费另列' if currency!='CNY' else '网页标价；目的地结算未核实，运费另列',
        planning_unit_allowance_cny=cap, confirmation_status='CANDIDATE_NOT_RELEASED',
        physical_test_status='NOT_TESTED', notes=note,
        alternative_and_readaptation='不得同名替换；重新核对电压、包络、孔位、引脚、质量和驱动。' ))

add('WH_FOC','左右轮驱，包含真实位置/速度反馈及驱动',2,'RIG-Hover: 4012 FOC，厂家完整型号/后缀 UNKNOWN','母线及连续/峰值额定 UNKNOWN',None,None,'轮毂直驱；轴/安装耳/轮胎接口 UNKNOWN','https://wiki.xgorobot.com/kb/pet-hover/b6eb0c96ae924758bff8ddd747bb79cd',route='FOC',cap=140,note='不是已购。同名4012不能推定尺寸40×12或7.4V。与当前Ø25皮带传动不同；报价、固件、协议单位、连续能力均阻塞。包含驱动的价格未知，禁止只计裸电机。')
add('WH_BRUSH','唯一关键替代：左右带AB编码器齿轮电机',2,'DFRobot FIT0521','电机额定6V；本候选按独立5V轨降额；编码器3.3V',{'diameter':24.4,'length':52},96,'PH2.0-6P；轴径/轴长/安装孔待图纸复核','https://www.dfrobot.com.cn/goods-1427.html',99,route='BRUSH',note='210rpm空载，3.2A/10kg·cm堵转；无连续额定。页面11×34.02=341.2算式错误，PPR倍频未冻结。官方效率/功率点亦不自洽。页面免邮不等于所有附件合单免邮。')
add('BR_DRV','替代轮驱H桥/硬件限流',2,'Pololu 4035 / DRV8874PWP carrier','VIN4.5–37V；厂商开放空气约2.1A连续',{'x':15.24,'y':17.78,'z':None},None,'2.54mm板孔；不以排针输送未经核验大电流','https://www.pololu.com/product/4035',11.94,'USD',route='BRUSH',note='设约1.5A限流后台架校准；默认约4.4A不适用本电机。PH/EN为drive/brake，SLEEP低才coast。缺货/允许backorder，交期未知。')
add('BR_REG','替代方案独立5V轮轨',1,'DFRobot DFR0753','6–14V输入；5V输出；8A是网页额定、封闭腔温升未测',None,None,'VIN/GND/5V/GND；接点额定待核','https://www.dfrobot.com.cn/goods-2971.html',55,route='BRUSH',note='不得把2S8.4V直接给6V电机然后只限制PWM。降压器不保证吸收回灌；轮轨仍需独立制动消能。')
add('HD_SERVO','头部yaw及pitch位置舵机',2,'FEETECH FT90M-FB（必须带-FB）','选择稳压5V；厂家PDF列3/4.8/6V测试',{'body_nominal':[23.2,12,25.5],'drawing_max_including_ears_spline':[32.6,12.19,28.55],'mount_centers':28.5,'mount_hole_diameter':2},12.5,'20T花键；塑料舵盘；孔距28.5±0.1，孔Ø2±0.1；线250mm','https://www.feetechrc.com/Data/feetechrc/upload/file/20220614/6379081252829481196832147.pdf',cap=30,note='280°/500–2500us；900/1500/2100us反馈0.04/1.65/3.2V，不能外推全行程。尺寸正文23.2和图23.3有差异，采用图的上限。6V堵转1A/2.15kg·cm不是连续能力。官网额定0.71kg·cm与PDF无对应连续条目，5V连续能力待测。')
add('MCU','运动/交互主控模块',2,'Espressif ESP32-S3-WROOM-1-N16R8','3.0–3.6V；16MB Quad Flash / 8MB Octal PSRAM',{'x':18,'y':25.5,'z':3.1},None,'41pad SMD；天线端另留15mm无铜/无器件区','https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.html',cap=30,note='选模组，不是71mm开发板，也不是裸芯片。LCSC C2913202搜索价USD5.8801未取得当前国内单只结算报价，主价留空；焊接/载板费用另列。GPIO35/36/37被R8 PSRAM占用。',channel='https://www.lcsc.com/product-detail/C2913202.html')
add('IMU','刚性机身IMU',1,'Adafruit 4438 LSM6DSOX breakout','3.3V供电及逻辑；SPI+INT1',{'x':25.6,'y':17.8,'z':4.6},1.7,'安装孔/连接器突出另核；不装头部','https://www.adafruit.com/product/4438',11.95,'USD',note='裸PCB包络可入26×18×5；插头/应力释放不能挤进剩余0.4mm。')
add('LCD','纯黑底双眼圆屏',1,'Waveshare 19192 / 1.28inch LCD Module / GC9A01','3.3V供电与逻辑；240×240 RGB565 SPI',{'active_diameter':32.4,'glass_diameter':37.5,'pcb_xy':[40.4,37.5],'assembled_z':None},None,'8线VCC/GND/DIN/CLK/CS/DC/RST/BL；实际端子编号未核','https://www.waveshare.com/1.28inch-lcd-module.htm',14.99,'USD',note='不可把32.4mm显示区画成58mm；含连接器厚度与安装孔需原图。31.2mA网页工作值缺亮度/电压条件，功耗模型留余量。')
add('CAM','按需照片和持续跟踪摄像头',1,'Arducam M0031 OV2640 DVP 24-pin CCM','传感器多电源轨/24pin次序须原厂模块图确认',None,None,'24pin FPC：间距、接触面、长度、引脚尚未冻结','https://www.arducam.com/arducam-ov2640-camera-module-2mp-mini-ccm-compact-camera-modules-compatible-with-arduino_m0031esp32-esp8266-development-board-with-dvp-24-pin-interface_.html',cap=30,note='OV2640支持JPEG不代表模块自带全部稳压或3.3V容限；禁止24pin通用接线。14×8×10mm预留尚无法确认，暂不可采购/定板。')
add('MIC','单麦克风',1,'DFRobot SEN0327 I2S MEMS microphone','1.8–3.3V；I2S；L/R选择',{'diameter':14,'z':None},None,'VCC/GND/SCK/WS/SD/LR；开孔和隔振垫另计','https://www.dfrobot.com.cn/goods-2567.html',15,note='不是已核实INMP441芯片；以SEN0327型号冻结采购对象。')
add('AMP','I2S扬声器功放',1,'DFRobot DFR0954 MAX98357A','5V；8Ω1.8W能力，软件/增益限制匹配扬声器',None,None,'I2S BCLK/LRC/DIN；SD低静音；BTL OUT+/OUT-均非地','https://www.dfrobot.com.cn/goods-3573.html',30,note='官方中文商品页未给完整尺寸；22×18×6只是机械预留。需取得CAD。AEC参考来自实际送DAC的PCM。')
add('SPK','扬声器尺寸/电气参考件',1,'Adafruit 1890 Mini Metal Speaker','8Ω；额定0.25W、最大0.5W',{'diameter':28,'z':4.5},6,'两根线；隔离声腔/密封垫需设计','https://www.adafruit.com/product/1890',1.95,'USD',note='官网当前Out of stock；属于可核验参考候选，供应门槛未过。不得把最大0.5W当连续；限Vrms≤sqrt(.25×8)=1.414V并测失真。')
add('BAT','工厂组装带保护2S电池包',1,'ANSMANN 2447-0105','Li-ion 2S1P 7.2V 3350mAh；满充8.4V；标称最大放电5A',{'x':39,'y':71,'z':18},99,'工厂12cm引线；订货需防呆插头，禁止用户焊裸电芯','https://batterie-boutique.fr/media/d3/cd/ed/1762344143/2447-0105_Lithium-Ionen-Akkupack.pdf?ts=1762344143',30.95,'EUR',note='含保护不等于有均衡/支持回灌。保护门槛、连续放电定义、最大充电电流、认证运输与国内到货价待核。核心可入40×72×22，但接头/减振净空不够。€30.95含德国19%VAT，出口税处理未知。',channel='https://www.reichelt.de/de/de/shop/produkt/lithium-ionen_akkupack_7_2_v_3350_mah_2s1p-414412')
add('CHG','5V升压2S CC/CV充电候选',1,'DFRobot DFR0564 / SY6982C','3–6V输入；8.4V±1%输出；最大1A（输入功率限制）',{'x':28,'y':37,'z':None,'heatsink':[14,14,7]},None,'microUSB/输入焊盘；改用独立USB-C合规输入','https://www.dfrobot.com.cn/goods-1706.html',30,note='非均衡、无LOAD电源路径。仅系统物理断开且托架上充电；保护包是否允许不均衡长期充电尚未确认。不能宣称充电链匹配已成立。')
add('REG_3V3','运动与交互分支稳压',2,'DFRobot DFR0570','5.5–28V输入；3.3V±0.1V；连续热额定待测',{'x':16.5,'y':22,'z':None},None,'两条独立逻辑分支；各自保护和去耦','https://www.dfrobot.com.cn/goods-1788.html',15,note='页面3A标题与2.4A峰值描述冲突；模型每域目标≤0.7A，不宣称3A连续。高电流马达不穿此板。')
add('REG_HEAD','头部与功放5V轨',1,'DFRobot DFR0753','6–14V输入；5V输出；封闭腔热验证待做',None,None,'两舵机并发约2A上界+音频；电流硬限值待量测','https://www.dfrobot.com.cn/goods-2971.html',55,note='5V舵机轨；不可用8.4V加降低PWM解释供电安全。不能假设此buck吸收再生电流。')
add('PWR_MON','电池电压/电流/功率监测',1,'DFRobot SEN0291 INA219 module','26V共模；10mΩ分流；地址默认0x45',{'x':30,'y':22,'z':None},4,'VIN+到电池保险后；VIN-到系统负载；Kelvin取样；端子额定待核','https://www.dfrobot.com.cn/goods-1890.html',39,note='不是硬件过流切断；软件低电预警早于BMS。充电系统关闭时不记录完整充电电量；需要独立充电测试仪。')
add('USB_C','唯一外观USB-C充电入口',1,'GCT USB4105-GF-A + TI TUSB320LAIRWBR + TPS2553DBVR (候选组合)','5V Type-C sink，双CC Rd/识别电流广告；不申请9/12/20V',None,None,'器件封装/输入限流/ESD未完成核对','https://www.ti.com/product/TUSB320LAI',cap=15,note='CC拉电阻仅建立连接，不自动获得3A。TPS2553电流设定与Rp识别真值表待设计；未冻结不要布PCB。')
add('SAFE','主电源/独立执行器急停/硬件禁止/保险反接保护',1,'完整器件后缀待限流与制动试验目标冻结','电池最高8.4V，目标5A分支协调，实际额定待选',None,None,'常闭急停独立于MCU；逻辑可留电，执行器总轨硬切','',cap=30,note='物理急停会导致失衡；必须外部保护。外部watchdog和本机ARM门控防上电自启；不能仅用普通开关或软件按钮代替。')
add('BRAKE','轮轨再生制动/过压消能',1,'比较器+MOSFET+脉冲电阻候选，阈值依轮驱最大母线确定','FOC轮轨或有刷5V轮轨分别设计',None,None,'就近驱动母线，不跨反向阻断器件回灌电池','',cap=20,note='1000uF无法吸收典型整机动能；未获驱动绝对最大电压不能定TVS/钳位阈值。')
add('IO_SAFE','跨电源域及舵机信号电平转换',4,'TI SN74LVC1T45DBVR','双电源，UART两相反方向+2路5V舵机PWM',{'package':'SOT-23-6; datasheet land pattern pending'},None,'Ioff；DIR固定；各VCC去耦；具体关断行为需原理图审查','https://www.ti.com/product/SN74LVC1T45',cap=2,note='不能用单片同DIR双通道芯片接全双工UART。FB另用20k/10k分压及RC/钳位，电阻与保护另计。')
add('PASSIVE','电阻电容ESD测试点摄像头稳压及连接器小料',1,'按最终原理图逐料展开，当前为未报价工程包','包含USB低电容ESD、100uF/10uF/100nF、CC、ADC、EN、boot、音频掉电隔离缓冲及保护',None,None,'不可遗漏；不将打包额度当精确BOM','',cap=30)
add('PCB','一次原型载板打样及钢网/组装',1,'V1模块载板（四层候选，外形待机械确认）','无Gerber报价；组装不能按已有工具抵零',{'proposed_board':[96,76,1.6]},None,'安装耳/天线/插头净空另核','',cap=55,note='此为额度非工厂报价；底层连续地面，DVP/SPI/I2S与大电流区分隔；不能声称2层必可。')
add('HARNESS','电池/电机线束与防呆端子',1,'AMASS XT30U-M/F；JST PHR/BnB-PH及SPH-002T-P0.5S候选，数量按线束表展开','大电流20AWG，信号26–28AWG；温升及压接待测',None,None,'原厂端子方向和线规必须复核；不使用杜邦或面包板承大电流','',cap=25)
add('MECH_DRIVE','轮胎、轮轴、传动/轴承/连接件',1,'2×Ø95×18轮胎；Ø6×13×4轮轴承×4；yaw20×32×7×1；pitch5×12×4×2；皮带/轮毂按路线','具体厂家及后缀待轴承/轴图确认',None,None,'FOC直驱与有刷皮带不能共用定孔图；皮带节距/齿数不由示意半径推断','',cap=45)
add('FASTEN','紧固件/嵌件/密封/声腔及隔振',1,'M2/M3按机械BOM核对后精确数量采购','材质/头型/长度/嵌件后缀待确认',None,None,'不把模型试打孔当公差完成','',cap=20)
add('PRINT','首套机壳/轮毂/托架及试打材料',1,'PLA/PETG/TPU按机械体积、支撑和废料计算','有效填充率沿用机械假设，再做±20%/30%敏感性',None,None,'材料成本率待供应报价；打印服务/机时若外包另计','',cap=52,note='机械打印件490.65g×1.20支撑废料＋托架/试打150g，按假设70元/kg约51.71元；52是估算额度，非报价/服务总价。非已有免费；轮胎若外购则TPU不重复计。')
add('SHIP','所有渠道运费与跨境税费',1,'按最终目的地合单报价','未核价',None,None,'不得假定进口免运费/免税','',cap=35)

doc=dict(revision=REV,status='PROTOTYPE_SELECTION_GATE_BLOCKED',accessed=DATE,
    budget_cny={'main_target':900,'hard_limit':1000,'reserve':100},
    fx_cny_per_unit={'CNY':1,'USD':7.2,'EUR':8.0},fx_status='ASSUMED planning factors, not current exchange-rate quotes',
    wake_model_cost='Not a material BOM item; free community request has uncertain acceptance/delivery; paid customization unquoted. Feature acceptance BLOCKED.',
    items=rows)
(OUT/'bom_candidates.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
with (OUT/'bom_candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
    for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
print(f'Wrote {len(rows)} explicit candidate/cost rows; unquoted prices remain null.')

if __name__=='__main__':
    assert sum(r['quantity'] for r in rows if r['id'] in ['WH_FOC','HD_SERVO'])==4
    assert sum(r['quantity'] for r in rows if r['id']=='MCU')==2
